import difflib
import logging
import os
from concurrent.futures import ThreadPoolExecutor
import re, json
from typing import Dict
from ...common.config import INVISIBLE_ORIGINAL,INVISIBLE_TRANSLATED, cfg
from ..utils.subtitles import get_original_and_translated
from ..bk_asr.ASRData import split_line, ASRData
import retry
from openai import OpenAI

from .subtitle_config import (
    TRANSLATE_PROMPT,
    OPTIMIZER_PROMPT,
    REFLECT_TRANSLATE_PROMPT,
    SINGLE_TRANSLATE_PROMPT,
    SINGLE_BATCH_TRANSLATE_PROMPT,
    SINGLE_BATCH_SYSTEM_PROMPT,
)
from ..subtitle_processor.aligner import SubtitleAligner
from ..utils import json_repair
from ..utils.logger import setup_logger

logger = setup_logger("subtitle_optimizer")

BATCH_SIZE = 20
MAX_THREADS = 10
DEFAULT_MODEL = "gpt-4o-mini"

class SubtitleOptimizer:
    """A class for optimize and translating subtitles using OpenAI's API."""
    allow_running = [True]
    original_language = None

    def __init__(
        self,
        model: str = cfg.model.value,
        summary_content: str = "",
        thread_num: int = cfg.thread_num.value,
        batch_num: int = cfg.batch_size.value,
        target_language: str = cfg.target_language.value,
        llm_result_logger: logging.Logger = None,
        need_remove_punctuation: bool = cfg.needs_remove_punctuation.value,
        cjk_only: bool = True,
        single_sentence_translate = False,
        allow_running = None,
        original_language = cfg.transcribe_language.value,
        custom_prompt = None,
    ) -> None:
        base_url = cfg.api_base.value
        api_key = cfg.api_key.value
        # assert base_url and api_key, "环境变量 OPENAI_BASE_URL 和 OPENAI_API_KEY 必须设置"

        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

        self.summary_content = summary_content
        self.prompt = TRANSLATE_PROMPT
        self.target_language = target_language
        self.batch_num = batch_num
        self.thread_num = thread_num
        self.executor = ThreadPoolExecutor(max_workers=thread_num)  # 创建类级别的线程池
        self.llm_result_logger = llm_result_logger
        self.need_remove_punctuation = need_remove_punctuation
        self.cjk_only = cjk_only
        self.single_sentence_translate = single_sentence_translate
        self.custom_prompt = custom_prompt
        
        if allow_running:
            self.allow_running = allow_running

        if original_language:
            self.original_language = original_language
            
        # 注册退出处理
        import atexit
        atexit.register(self.stop)

    def stop(self):
        """关闭线程池"""
        if hasattr(self, 'executor') and hasattr(self.executor, '_threads'):
            print("正在强制关闭线程池")
            for future in self.executor._threads:
                try:
                    future._tstate_lock.release()
                    future._stop()
                except Exception:
                    pass
            #  关闭线程池
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.executor = None


    def optimizer_multi_thread(self, subtitle_json: Dict[int, str],
                               translate=False,
                               reflect=False,
                               callback=None,
                               ):
        batch_num = self.batch_num
        items = list(subtitle_json.items())[:]
        chunks = [dict(items[i:i + batch_num]) for i in range(0, len(items), batch_num)]

        def process_chunk(chunk):
            for key in chunk:
                # set chunk to original only
                chunk[key], _ = get_original_and_translated(chunk[key])
            
            if not self.allow_running[0]:
                return
            failed = False
            if translate:
                try:
                    result = self.translate(chunk, reflect)
                except Exception as e:
                    logger.error(f"翻译失败，使用单条翻译：{e}")
                    # logger.info(f"chunk len:{len(chunk)}\n{chunk}")
                    failed = True
                    # result = self.translate_single(chunk)
            else:
                try:
                    result = self.optimize(chunk)
                except Exception as e:
                    logger.error(f"优化失败：{e}")
                    result = chunk
            
            if failed:
                result = self.translate_single(chunk)
                failed = False
            
            for key in result:
                # Put the invisible label back
                lines = result[key].split("\n")
                if len(lines) > 1:
                    translate_line = " ".join(lines[1:]) # The translate result is in the second line.
                else:
                    translate_line = lines[0]
                # Splite the line according to cfg
                translate_line = split_line(translate_line, cfg.max_char_count_english.value, cfg.max_char_count_cjk.value)
                original_line = split_line(chunk[key], cfg.max_char_count_english.value, cfg.max_char_count_cjk.value)
                result[key] = INVISIBLE_ORIGINAL + original_line + "\n" + INVISIBLE_TRANSLATED + translate_line

            if callback:
                if isinstance(result, Dict):
                    callback(result)
            return result

        results = list(self.executor.map(process_chunk, chunks))
        if not self.allow_running[0]:
            logger.error("优化/翻译过程时中断")

        # 合并结果
        optimizer_result = {k: v for result in results for k, v in result.items()}
        return optimizer_result
    
    @retry.retry(tries=1)
    def optimize(self, original_subtitle: Dict[int, str]) -> Dict[int, str]:
        if not self.allow_running[0]:
            logger.error("优化/翻译过程时中断")
        
        """ Optimize the given subtitle. """
        logger.info(f"[+]正在优化字幕：{next(iter(original_subtitle))} - {next(reversed(original_subtitle))}")

        message = self._create_optimizer_message(original_subtitle)

        response = self.client.chat.completions.create(
            model=self.model,
            stream=False,
            messages=message,
            timeout=80)

        optimized_text = json_repair.loads(response.choices[0].message.content)

        aligned_subtitle = repair_subtitle(original_subtitle, optimized_text)  # 修复字幕对齐问题

        for k, v in aligned_subtitle.items():
            optimized_text = self.remove_punctuation(v)
            aligned_subtitle[k] = optimized_text
            self.llm_result_logger.info(f"优化字幕：{original_subtitle[k]}")
            self.llm_result_logger.info(f"优化结果：{optimized_text}")
            self.llm_result_logger.info("===========")
            if not self.allow_running[0]:
                logger.error("optimize 优化/翻译过程时中断")
                break

        return aligned_subtitle

    @retry.retry(tries=1)
    def translate(self, original_subtitle: Dict[int, str], reflect=False) -> Dict[int, str]:
        if not self.allow_running[0]:
            logger.error("单句 优化/翻译过程时中断")
            return

        """优化并翻译给定的字幕。"""
        if reflect:
            return self._reflect_translate(original_subtitle)
        else:
            return self._normal_translate(original_subtitle)

    def _reflect_translate(self, original_subtitle: Dict[int, str]):
        logger.info(f"[+]正在反思翻译字幕：{next(iter(original_subtitle))} - {next(reversed(original_subtitle))}")
        message = self._create_translate_message(original_subtitle)
        response = self.client.chat.completions.create(
            model=self.model,
            stream=False,
            messages=message,
            temperature=0.7)
        response_content = json_repair.loads(response.choices[0].message.content)
        # print(response_content)
        optimized_text = {k: v["optimized_subtitle"] for k, v in response_content.items()}  # 字幕文本
        aligned_subtitle = repair_subtitle(original_subtitle, optimized_text)  # 修复字幕对齐问题
        # print(aligned_subtitle)
        # 在 translations 中查找对应的翻译  文本-翻译 映射
        translated_subtitle = {}
        translations = {}
        for item in response_content.values():
            key = item["optimized_subtitle"]
            revised = item["revised_translation"]
            # Sometimes the revised_translation is empty.
            translations[key] = revised if revised else item["translation"]
            
        # translations = {item["optimized_subtitle"]: item["revised_translation"] for item in response_content.values()}
        
        for k, v in aligned_subtitle.items():
            original_text = self.remove_punctuation(v)
            translated_text = self.remove_punctuation(translations.get(v, ' '))
            translated_subtitle[k] = f"{original_text}\n{translated_text}"

        if self.llm_result_logger:
            for k, v in response_content.items():
                self.llm_result_logger.info(f"原字幕：-----")
                self.llm_result_logger.info(f"优化字幕：{v['optimized_subtitle']}")
                self.llm_result_logger.info(f"翻译后字幕：{v['translation']}")
                self.llm_result_logger.info(f"反思后字幕：{v['revised_translation']}")
                self.llm_result_logger.info("===========")
        return translated_subtitle

    def _normal_translate(self, original_subtitle: Dict[int, str]):
        logger.info(f"[+]正在翻译字幕：{next(iter(original_subtitle))} - {next(reversed(original_subtitle))}")
        prompt = TRANSLATE_PROMPT.replace("[TargetLanguage]", self.target_language)
        message = [{"role": "system", "content": prompt},
                   {"role": "user",
                    "content": f"Please translate the input into {self.target_language}:\n<input>{str(original_subtitle)}</input>"}]
        response = self.client.chat.completions.create(
            model=self.model,
            stream=False,
            messages=message,
            temperature=0.7)
        response_content = json_repair.loads(response.choices[0].message.content)
        assert isinstance(response_content, dict) and len(response_content) == len(original_subtitle), "翻译结果错误"
        # logger.info(f"翻译结果：{next(iter(original_subtitle))} - {next(reversed(original_subtitle))}, 翻译条数：{len(response_content)}")
        translated_subtitle = {}
        original_list = list(original_subtitle.values())
        translated_list = list(response_content.values())
        for i, key in enumerate(original_subtitle.keys()):
            original_text = self.remove_punctuation(original_list[i])
            translated_text = self.remove_punctuation(translated_list[i])
            translated_subtitle[key] = f"{original_text}\n{translated_text}"

        return translated_subtitle

    def _create_translate_message(self, original_subtitle: Dict[int, str]):
        input_content = f"correct the original subtitles, and translate them into {self.target_language}:\n<input_subtitle>{str(original_subtitle)}</input_subtitle>"
        if self.summary_content:
            input_content += f"\nThe following is reference material related to subtitles, based on which the subtitles will be corrected, optimized, and translated:\n<prompt>{self.summary_content}</prompt>\n"
        prompt = REFLECT_TRANSLATE_PROMPT.replace("[TargetLanguage]", self.target_language)
        if self.custom_prompt:
            prompt += "\nAdditional Info:\n" + self.custom_prompt
        message = [{"role": "system", "content": prompt},
                   {"role": "user", "content": input_content}]
        return message

    def _create_optimizer_message(self, original_subtitle):
        input_content = f"Optimize the following subtitles:\n<input_subtitle>{str(original_subtitle)}</input_subtitle>"
        if self.summary_content:
            input_content += f"\nThe following is reference material related to subtitles, based on which the subtitles will be corrected and optimized.:\n<prompt>{self.summary_content}</prompt>\n"
        message = [{"role": "user", "content": OPTIMIZER_PROMPT},
                   ]
        return message

    def translate_single(self, original_subtitles: Dict[int, str]) -> Dict[int, str]:
        
        """单条字幕翻译，用于在批量翻译失败时的备选方案"""
        translate_result = {}
        if not self.allow_running[0]:
            logger.error("单句 翻译过程时中断")
            return translate_result

        # logger.info(f"org sub:{original_subtitle}")
        for key, value in original_subtitles.items():
            try:
                sys_prompt = SINGLE_TRANSLATE_PROMPT.replace("[TargetLanguage]", self.target_language)
                message = [{"role": "system", "content": sys_prompt},
                           {"role": "user", "content": value}]
                response = self.client.chat.completions.create(
                    model=self.model,
                    stream=False,
                    messages=message)
                logger.info(f"response: {response}\n")
                translate = response.choices[0].message.content.replace("\n", "")
                original_text = self.remove_punctuation(value)
                translated_text = self.remove_punctuation(translate)
                translate_result[key] = f"{original_text}\n{translated_text}"
                logger.info(f"单条翻译结果: {translate_result[key]}")
            
                if not self.allow_running[0]:
                    logger.error("单句 翻译过程时中断")
                    break
            except Exception as e:
                 logger.error(f"单条翻译失败: {e}")
                 translate_result[key] = f"{value}\n "
        return translate_result

    def translate_single_batch(self, asr_data: ASRData , callback = None) -> Dict[int,str]:
        """直接大批翻译字幕"""
        translate_result = {}
        previous_sentence = ""
        previous_translation = ""
        re_remove_think = re.compile(r".*<\/think>")
        re_translate = re.compile(r".*<[Tt]ranslation>(.*?)</[Tt]ranslation>")
        re_notag = re.compile(r"<.*?>")

        subtitle_json = asr_data.to_json()
        original_subtitle = {str(k): v["original_subtitle"] for k, v in subtitle_json.items()}
        
        print(f"Target language: {self.target_language}")

        sys_prompt = SINGLE_BATCH_SYSTEM_PROMPT.replace("[TargetLanguage]", self.target_language
                    ).replace("[OriginalLanguage]", self.original_language)
        
        if self.custom_prompt:
            sys_prompt += "\nAdditional info:\n" + self.custom_prompt
        
        for key, value in original_subtitle.items():
            
            if "\n" in value:
                # Only need original, discard the translated
                original, _ = get_original_and_translated(value)
            else:
                original = value
            
            if not self.allow_running[0]:
                logger.error("单句批量 翻译过程时中断")
                return translate_result
            
            # content = SINGLE_BATCH_TRANSLATE_PROMPT.replace("[TargetLanguage]", self.target_language
            #     ).replace( "[PreviousSentence]", previous_sentence
            #     ).replace( "[PreviousTranslation]", previous_translation)
            
            if previous_sentence:
                # Calculate the time difference between last sentence and this sentence
                # If it's over 2000 ms, then no need for showing the previous sentence.
                
                pre_end_time = subtitle_json[str( int(key)-1 )]["end_time"]
                time_diff = subtitle_json[key]["start_time"] - pre_end_time
                if time_diff > 2000:
                    message = [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": original}
                    ]
                else:
                    message =[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": previous_sentence},
                        {"role": "assistant", "content": previous_translation},
                        {"role": "user", "content": original}
                    ]
            else:
                message =[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": original}
                ]
            
            previous_sentence = original

            response = self.client.chat.completions.create(
                model=self.model,
                stream=False,
                messages=message)

            return_text = response.choices[0].message.content
            # logger.info(f"response:{type(return_text)}")
            
            # print(f"reply: {return_text}")
            # Single line only.
            return_text = return_text.replace("\n", " ").strip()
            
            # Remove all <think> </think> tags
            text = re.sub(re_remove_think, "", return_text )

            # Remove the remaining tags, just in case.
            translated = re.sub(re_notag, "", text)

            # Remove punctuation
            original = self.remove_punctuation(original)
            translated = self.remove_punctuation(translated)
            
            # Fix the sentence ending problem in Chinese
            # print (f"original: {self.original_language} target:{self.target_language}")
            if self.original_language == "English" and self.target_language == "简体中文":
                if ( original[-1] != "." and translated[-1] == "。") \
                        or (original[-1] != "?" and translated[-1] == "？") :
                    translated = translated[:-1]

            # Special handling for sound descriptions
            if original[0]=="[" and original[-1]=="]":
                if translated[0] != "[":
                    translated = "[" + translated
                if translated[-1] != "]":
                    translated = translated + "]"

            previous_translation = translated
            logger.info(f"{key}. Original: {value}\n{key}. Translated: {translated}")
            
            # Split by cfg settings
            original = split_line(original, cfg.max_char_count_english.value, cfg.max_char_count_cjk.value)
            translated = split_line(translated, cfg.max_char_count_english.value, cfg.max_char_count_cjk.value)
            line = {str(key): INVISIBLE_ORIGINAL+ original + "\n" + INVISIBLE_TRANSLATED + translated}  # Create a dictionary with key and translated text

            if callback:
                # report the progress
                callback(line)
            
            translate_result.update(line)      # Add line to result
        return translate_result

    

    def remove_punctuation(self, text: str) -> str:
        """
        移除字幕中的标点符号
        """
        cjk_only = self.cjk_only
        need_remove_punctuation = self.need_remove_punctuation
        def is_mainly_cjk(text: str) -> bool:
            """
            判断文本是否主要由中日韩文字组成
            """
            # 定义CJK字符的Unicode范围
            cjk_patterns = [
                r'[\u4e00-\u9fff]',           # 中日韩统一表意文字
                r'[\u3040-\u309f]',           # 平假名
                r'[\u30a0-\u30ff]',           # 片假名
                r'[\uac00-\ud7af]',           # 韩文音节
            ]
            cjk_count = 0
            for pattern in cjk_patterns:
                cjk_count += len(re.findall(pattern, text))
            total_chars = len(''.join(text.split()))
            return cjk_count / total_chars > 0.4 if total_chars > 0 else False

        punctuation = r'[,.!?;:，。！？；：、]'
        if not need_remove_punctuation or (cjk_only and not is_mainly_cjk(text)):
            return text
        # 移除末尾标点符号
        return re.sub(f'{punctuation}+$', '', text.strip())


def repair_subtitle(dict1, dict2) -> Dict[int, str]:
    list1 = list(dict1.values())
    list2 = list(dict2.values())
    text_aligner = SubtitleAligner()
    aligned_source, aligned_target = text_aligner.align_texts(list1, list2)

    assert len(aligned_source) == len(aligned_target), "对齐后字幕长度不一致"
    # 验证是否匹配
    similar_list = calculate_similarity_list(aligned_source, aligned_target)
    if similar_list.count(True) / len(similar_list) >= 0.89:
        # logger.info(f"修复成功！序列匹配相似度：{similar_list.count(True) / len(similar_list):.2f}")
        start_id = next(iter(dict1.keys()))
        modify_dict = {str(int(start_id) + i): value for i, value in enumerate(aligned_target)}
        return modify_dict
    else:
        logger.error(f"修复失败！相似度：{similar_list.count(True) / len(similar_list):.2f}")
        logger.error(f"源字幕：{list1}")
        logger.error(f"目标字幕：{list2}")
        raise ValueError("Fail to repair.")


def is_similar(text1, text2, threshold=0.4):
    similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
    return similarity >= threshold


def calculate_similarity_list(list1, list2, threshold=0.5):
    max_len = min(len(list1), len(list2))
    similar_list = [False] * max_len  # 初始化相似性列表

    for i in range(max_len):
        similar_list[i] = is_similar(list1[i], list2[i], threshold)

    return similar_list


if __name__ == "__main__":
    # os.environ['OPENAI_BASE_URL'] = 'https://api.gptgod.online/v1'
    # os.environ['OPENAI_API_KEY'] = 'sk-4StuHHm6Z1q0VcPHdPTUBdmKMsHW9JNZKe4jV7pJikBsGRuj'
    # MODEL = "gpt-4o-mini"
    os.environ['OPENAI_BASE_URL'] = 'https://api.turboai.one/v1'
    os.environ['OPENAI_API_KEY'] = 'sk-ZOCYCz5kexAS3X8JD3A33a5eB20f486eA26896798055F2C5'
    MODEL = "gpt-4o-mini"

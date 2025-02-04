import openai


def test_openai(base_url, api_key, model):
    """
    这是一个测试OpenAI API的函数。
    它使用指定的API设置与OpenAI的GPT模型进行对话。

    参数:
    user_message (str): 用户输入的消息

    返回:
    bool: 是否成功
    str: 错误信息或者AI助手的回复
    """
    try:
        # 创建OpenAI客户端并发送请求到OpenAI API
        response = openai.OpenAI(base_url=base_url, api_key=api_key, timeout=15).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            max_tokens=100,
            timeout=10
        )
        # 返回AI的回复
        return True, str(response.choices[0].message.content)
    except Exception as e:
        return False, str(e)


def get_openai_models(base_url, api_key):
    try:
        # 创建OpenAI客户端并获取模型列表
        models = openai.OpenAI(base_url=base_url, api_key=api_key, timeout=10).models.list()

        # 根据不同模型设置权重进行排序
        def get_model_weight(model_name):
            model_name = model_name.lower()
            if model_name.startswith(('gpt-4o', 'claude-3-5')):
                return 10
            elif model_name.startswith('gpt-4'):
                return 5
            elif model_name.startswith('claude-3'):
                return 6
            elif model_name.startswith(('deepseek', 'glm')):
                return 3
            return 0

        sorted_models = sorted(
            [model.id for model in models],
            key=lambda x: (-get_model_weight(x), x)
        )
        return sorted_models
    except Exception:
        return []


if __name__ == "__main__":
    print(test_openai("https://ddg.bkfeng.top/v1", "2", "gpt-4o-mini"))

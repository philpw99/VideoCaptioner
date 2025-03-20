import requests
import re

def get_douban_movie_info(id: str, topActors = 20):
    if not id.isdigit():
        return
    headers = {'user-agent': 'VideoCaptioner/3.5.4'}
    try:

        # Get summary
        r = requests.get(f"https://movie.douban.com/subject/{id}/", headers=headers)
        if r.status_code != 200:
            raise Exception(f"Problem getting douban summary info. code: {r.status_code}")

        text = r.content.decode()
        
        # Get summary
        match_summary = re.search(r"<span property=\"v:summary\">(.*?)<\/span>", text, re.RegexFlag.MULTILINE | re.DOTALL)
        if match_summary:
            summary = match_summary.group(1)
            summary = re.sub(r"\s\s+|\\n|\\u3000|<br \/>|<br>", " ", summary).strip()
        else:
            summary = ""
        
        # Get genre
        match_genre = re.search(r"<span property=\"v:genre\">(.*?)<\/span>", text)
        if match_genre:
            genre = match_genre.group(1)
        else:
            genre = ""
        
        # Get year
        match_year = re.search(r"<span class=\"year\">\((.*?)\)<\/span>", text)
        if match_year:
            year = match_year.group(1)
        else:
            year = ""

        if text.find("<span class=\"pl\">片长:</span>") != -1:
            kind = "电影"
        elif text.find("<span class=\"pl\">集数:</span>") != -1:
            kind = "电视剧"
        else:
            kind = "视频"

        # Get Post URL
        match_post = re.search(r"<img src=\"(.*?)\" title=\"点击看更多海报\".*?rel=\"v:image\">", text)
        if match_post:
            post_url = match_post.group(1)
        else:
            post_url = ""

        # Get actors
        r = requests.get(f"https://movie.douban.com/subject/{id}/celebrities", headers=headers)
        if r.status_code != 200:
            raise Exception(f"Problem getting douban actors info. code: {r.status_code}")

        text = r.content.decode()
        match_actors = re.findall(r"\(饰 (.*?)\)", text)
        if not match_actors:
            # 动画之类的会是配音，而不是饰演
            match_actors = re.findall(r"\(配 (.*?)\)", text)
            
        actors = ", ".join( actor for actor in match_actors[:topActors*2:2]) if match_actors else " "    # only keep odd lines in the list

        movie_info=f"这是一出 {year}年 {genre} {kind}.\n" \
            + "剧情:\n" \
            + f"{summary}\n" \
            + f"人物: {actors}"
        
        return movie_info, post_url, kind

    except Exception as e:
        print(e)

if __name__ == "__main__":
    get_douban_movie_info("36774001")
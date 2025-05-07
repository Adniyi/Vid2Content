# from pytube import YouTube
import yt_dlp
from typing import Dict,List

def extract_video_id(data: Dict) -> str:
    """
    Extracts the video ID from the provided data dictionary.

    Args:
        data: A dictionary containing video information, assumed to have an 'id' key.

    Returns:
        The video ID as a string, or an empty string if not found.
    """
    if isinstance(data, dict) and 'id' in data:
        return data['id']
    return ''

def construct_thumbnail_urls(video_id: str) -> Dict[str, str]:
    """
    Constructs various YouTube thumbnail URLs from a given video ID.

    Args:
        video_id: The YouTube video ID.

    Returns:
        A dictionary containing different thumbnail URLs.
    """
    if not video_id:
        return {}

    base_url = f"https://img.youtube.com/vi/{video_id}"
    thumbnail_urls = {
        "default":   f"{base_url}/default.jpg",
        "medium":    f"{base_url}/mqdefault.jpg",
        "high":      f"{base_url}/hqdefault.jpg",
        "sd":        f"{base_url}/sddefault.jpg",
        "maxres":    f"{base_url}/maxresdefault.jpg",
    }
    return thumbnail_urls


def get_thumbnail_urls(data: Dict) -> Dict[str, str]:
    """
    Combines the extraction and construction steps to get thumbnail URLs
    from the provided data.

    Args:
        data:  A dictionary containing video information.

    Returns:
        A dictionary of thumbnail URLs, or an empty dictionary if the
        video ID could not be extracted.
    """
    video_id = extract_video_id(data)
    if not video_id:
        return {}
    return construct_thumbnail_urls(video_id)






# video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# with yt_dlp.YoutubeDL({'quiet':True}) as ydl:
#     info_dict = ydl.extract_info(video_url, download=False)
#     title = info_dict.get('title', 'audio')
#     video_format = info_dict.get('formats')
#     thumbnail_url = get_thumbnail_urls(info_dict)
#     length = info_dict.get('duration_string')

# print(title)
# print(thumbnail_url['default'])
# print(length)
# # print(info_dict)
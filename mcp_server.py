import gradio as gr
import redditwarp.SYNC
import pandas as pd
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup, NavigableString
import httpx
client = redditwarp.SYNC.Client()


def reddit_search(search_query:str,amount:int=10,subreddit:str='',min_comments_cnt:int=5,min_post_score:int=10,**kwargs):
    """
    Search query in reddit, return fetched posts with comment and information

    Args:
        search_query (str): The input text to search through
        amount (int): count posts to search

    Returns:
        pd.DataFrame: A message dictionary with titles, scores,comments and texts
    """
    search_response = client.p.submission.search(sr=subreddit,query=search_query,amount=amount*2,**kwargs)
    posts_data = [client.p.comment_tree.fetch(post.id) for post in search_response]
    posts = [post for post in posts_data if (post.value.comment_count>min_comments_cnt) and (post.value.score > min_post_score)]
    post_comments = { post.value.title:
                        {'comments':[comment.value.body for comment in post.children],
                        'score':post.value.score,
                        'comment_count':post.value.comment_count,
                        }
                    for post in posts[:amount]}
    return pd.DataFrame(post_comments).T.reset_index()

def duckduckgo_search(search_query):
    """
    Search query in internet via DuckDuckGo Search enginre

    Args:
        search_query (str): The input text to search through
        amount (int): count posts to search

    Returns:
        List[Dict]: List of search results with title,snippet and url to web resource
    """
    return pd.DataFrame(DDGS().text(search_query,region='ru-ru',safesearch='off')).to_markdown()


def parse_url(url:str):
    """ 
    Parse indeep info from web page. Get url and return all information than page have
    Args:
        url (str): url of web resource
        amount (int): count posts to search

    Returns:
        Str: Raw text results from web page
    """
    response = httpx.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'noscript', 'nav', 'footer', 'head', 'meta']):
        element.decompose()

    # Pre-process specific tags
    for br in soup.find_all('br'):
        br.replace_with('\n')
        
    # List of block-level elements that should have line breaks
    BLOCK_TAGS = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                  'ul', 'ol', 'li', 'hr', 'tr', 'td', 'th', 'section',
                  'article', 'header', 'table', 'pre']

    # Add line breaks before and after block elements
    for tag in soup.find_all(BLOCK_TAGS):
        if tag.previous_sibling and not isinstance(tag.previous_sibling, NavigableString):
            tag.insert_before('\n')
        if tag.next_sibling and not isinstance(tag.next_sibling, NavigableString):
            tag.insert_after('\n')

    # Get text with proper spacing
    text = soup.get_text(separator='\n', strip=True)
    
    # Clean up excessive whitespace
    text = '\n'.join([line.strip() for line in text.splitlines() if line.strip() if len(line.split(' ')) > 2])
    
    return text


with gr.Blocks() as demo:
    sq = gr.Textbox(label="Search_query")
    with gr.Tab('DuckDuckGo'):
        ddg_btn = gr.Button("DuckDuckGo Search")
        ddg_md = gr.Markdown()
        ddg_btn.click(duckduckgo_search,inputs=[sq],outputs=ddg_md)

    with gr.Tab('Reddit'):
        reddit_btn = gr.Button("Reddit Search")
        reddit_md = gr.Dataframe()
        reddit_btn.click(reddit_search,inputs=[sq],outputs=reddit_md)

    with gr.Tab('ParseURL'):
        URL = gr.Textbox("URL")
        parse_btn = gr.Button("Parse URL")
        parse_btn.click(parse_url,inputs=[URL],outputs=gr.Text())
        
        
demo.launch(mcp_server=True,show_api=True)

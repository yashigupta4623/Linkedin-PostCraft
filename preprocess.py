import json
from llm_helper import llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException


def process_posts(raw_file_path, processed_file_path=None):
    """
    Processes LinkedIn posts by enriching them with metadata and unifying tags.
    
    Args:
        raw_file_path (str): Path to the raw posts JSON file.
        processed_file_path (str): Path to save the processed posts JSON file.
    """
    # Load raw posts from the specified file
    with open(raw_file_path, encoding='utf-8') as file:
        posts = json.load(file)
        enriched_posts = []

        # Enrich each post with metadata (line count, language, and tags)
        for post in posts:
            metadata = extract_metadata(post['text'])
            post_with_metadata = post | metadata  # Merge metadata into the post
            enriched_posts.append(post_with_metadata)

    # Unify tags across all posts to create a standardized tag set
    unified_tags = get_unified_tags(enriched_posts)
    for post in enriched_posts:
        current_tags = post['tags']
        # Replace current tags with their unified counterparts
        new_tags = {unified_tags[tag] for tag in current_tags}
        post['tags'] = list(new_tags)

    # Save the processed posts to the specified output file
    with open(processed_file_path, encoding='utf-8', mode="w") as outfile:
        json.dump(enriched_posts, outfile, indent=4)


def extract_metadata(post):
    """
    Extracts metadata (line count, language, and tags) from a LinkedIn post.
    
    Args:
        post (str): The text of the LinkedIn post.
        
    Returns:
        dict: Metadata including line count, language, and tags.
    """
    # Template for extracting metadata using LLM
    template = '''
    You are given a LinkedIn post. You need to extract number of lines, language of the post and tags.
    1. Return a valid JSON. No preamble. 
    2. JSON object should have exactly three keys: line_count, language and tags. 
    3. tags is an array of text tags. Extract maximum two tags.
    4. Language should be English or Hinglish (Hinglish means Hindi + English)
    
    Here is the actual post on which you need to perform this task:  
    {post}
    '''

    # Create a prompt from the template
    pt = PromptTemplate.from_template(template)
    chain = pt | llm  # Combine the prompt with the language model
    response = chain.invoke(input={"post": post})

    # Parse the response into JSON
    try:
        json_parser = JsonOutputParser()
        res = json_parser.parse(response.content)
    except OutputParserException:
        raise OutputParserException("Context too big. Unable to parse post metadata.")
    return res


def get_unified_tags(posts_with_metadata):
    """
    Generates a unified tag mapping to standardize tags across posts.
    
    Args:
        posts_with_metadata (list): List of posts enriched with metadata.
        
    Returns:
        dict: Mapping of original tags to unified tags.
    """
    # Collect all unique tags from the posts
    unique_tags = set()
    for post in posts_with_metadata:
        unique_tags.update(post['tags'])  # Add tags to the unique set

    # Convert the set of tags into a comma-separated string
    unique_tags_list = ','.join(unique_tags)

    # Template for unifying tags using LLM
    template = '''I will give you a list of tags. You need to unify tags with the following requirements,
    1. Tags are unified and merged to create a shorter list. 
       Example 1: "Jobseekers", "Job Hunting" can be all merged into a single tag "Job Search". 
       Example 2: "Motivation", "Inspiration", "Drive" can be mapped to "Motivation"
       Example 3: "Personal Growth", "Personal Development", "Self Improvement" can be mapped to "Self Improvement"
       Example 4: "Scam Alert", "Job Scam" etc. can be mapped to "Scams"
    2. Each tag should follow title case convention. Example: "Motivation", "Job Search"
    3. Output should be a JSON object. No preamble.
    4. Output should have mapping of original tag and the unified tag. 
       For example: {"Jobseekers": "Job Search", "Motivation": "Motivation"}
    
    Here is the list of tags: 
    {tags}
    '''

    # Create a prompt from the template
    pt = PromptTemplate.from_template(template)
    chain = pt | llm  # Combine the prompt with the language model
    response = chain.invoke(input={"tags": str(unique_tags_list)})

    # Parse the response into JSON
    try:
        json_parser = JsonOutputParser()
        res = json_parser.parse(response.content)
    except OutputParserException:
        raise OutputParserException("Context too big. Unable to parse tags.")
    return res


if __name__ == "__main__":
    # Entry point of the script; process the raw posts and save the processed posts
    process_posts("data/raw_posts.json", "data/processed_posts.json")

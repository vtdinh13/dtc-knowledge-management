# Phase 1
## Summary
### Problem:
 - How to acquire the transcripts: `yt-dlp` vs `YouTubeTranscriptApi`

### Result: 
- Used `yt-dlp` to acquire metadata  ML Zoomcamp metadata from YouTube
- Decided to use YouTubeTranscriptApi because parsing was much easier. There may be some tradeoff in the accuracy of the timestamps but it's not important for what I'm trying to achieve with this project.
## Procedure
1. Analyzed structure of YouTube URL
2. Extracted a list of playlist URLs
    - Two options: 
        1. YouTube Data API
            - has a free tier of 10,000 units a day and resets daily
            - must have a Google account
        2. **yt-dlp**
            - [+] don't need to set up API keys
            - [+] can extract entries without downloading videos 
3. `uv add yt-dlp` to install package to extract URLs from playlists
4. `uv add jupyterlab --dev` to install developmental version of jupyterlab for small experiments and tests
5. Cached ML Zoomcamp metadata as a local JSON file to avoid repeated network requests -> stored as `ml_zoomcamp_metadata.json`.
6. TESTING
    - [x] download one automatically generated transcript -> VTT file
    - [x] parse transcript -> didn't like results
    - [x] proceed with youtube transcript api to create transcriptions


# Phase 2
Problem: How to save data JSON file per video. This forms the basis for creating the data model in postgres later. 
Result: 

1. The first module consists of 10 videos. I selected the first three videos to experiment, assigned to the object `transcripts`. 
2. Begin building the data model. 
    - [x] extract metadata -> `module1` as a list of dict
        - id
        - title
        - duration
    - [x] extract timestamps + content 
    - [x] extract content only 
3. Create transcript extraction script -> `extract_transcripts.py`
    




-----
# Notes
1. `jupyter kernelspec list` to get a list of kernels
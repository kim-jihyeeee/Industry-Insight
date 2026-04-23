import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v14.0", layout="wide")

# 🌟 Gemini API 설정
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash-latest')
    except: return None

ai_engine = init_ai()

@st.cache_data
def load_font():
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        res = requests.get(url)
        with open("nanum_font.ttf", "wb") as f: f.write(res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 22px; margin: 5px; background-color: #fff; border: 2px solid #FFB300; border-radius: 5px; font-weight: bold; color: #333; font-size: 0.95em; }
    .section-header { font-size: 1.4em; font-weight: bold; margin: 30px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; color: #333; }
    </style>
""", unsafe_allow_html=True)

# 🌟 [v14.0 핵심] AI 분석 실패 시 데이터 기반 강제 추출 로직
def get_failsafe_keywords(titles):
    if not titles: return ["#데이터수집오류"]
    
    # 1단계: AI에게 전략 키워드 요청
    prompt = f"다음 뉴스 제목들에서 AE 제안서용 핵심 명사 5개만 #단어 형태로 뽑아줘. (이슈, 트렌드 같은 일반 명사 금지): {titles}"
    try:
        resp = ai_engine.generate_content(prompt)
        keywords = re.findall(r'#\w+', resp.text)
        if len(keywords) >= 5: return keywords[:5]
    except: pass

    # 2단계: AI 실패 시 직접 텍스트 분석 (빈도수 상위 명사 추출)
    combined_text = " ".join(titles)
    # 2글자 이상 한글 명사 형태만 추출
    words = re.findall(r'[가-힣]{2,}', combined_text)
    # 광고와 무관한 불용어 필터링
    stop_words = ['뉴스', '제목', '기자', '지난', '이번', '통해', '함께', '오전', '오후', '대한', '관련']
    filtered_words = [w for w in words if w not in stop_words]
    
    counts = Counter(filtered_words)
    top_5 = [f"#{w}" for w, c in counts.most_common(5)]
    
    return top_5 if top_5 else ["#분석데이터부족"]

def create_cleaned_wc(text_

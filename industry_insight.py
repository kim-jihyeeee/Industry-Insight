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
st.set_page_config(page_title="AE Total Tool v15.4", layout="wide")

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

# 🌟 네이버 데이터랩 쇼핑 인사이트 기준 전체 카테고리 세팅
DETAILED_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "스포츠의류", "아동의류", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계", "지갑/벨트", "모자", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어", "뷰티소품"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "영상가전", "이미용가전", "PC/노트북", "음향기기"],
    "식품": ["건강식품", "다이어트식품", "음료", "커피/차", "가공식품", "신선식품", "과자/베이커리"],
    "스포츠/레저": ["골프", "캠핑", "피트니스/요가", "등산", "낚시", "자전거", "수영"],
    "생활/건강": ["세탁/세정용품", "주방용품", "욕실용품", "반려동물", "의료기기", "생활용품", "문구/사무용품"],
    "출산/육아": ["분유/기저귀", "임부복/용품", "수유용품", "유모차/카시트", "아기물티슈", "목욕용품"]
}

# 세션 초기화 및 DB 열 이름 표준화 (KeyError 방지)
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

def normalize_column_names(df):
    rename_map = {
        '날짜': ['날짜', '일자', 'Date', '등록일'],
        '광고주명': ['광고주명', '광고주', '업체명', 'Client'],
        '소통내용': ['소통내용', '내용', '소통', '상담내용']
    }
    new_cols = {}
    for standard, variations in rename_map.items():
        for col in df.columns:
            if col in variations: new_cols[col] = standard
    return df.rename(columns=new_cols)

# 스타일 적용
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 8px 18px; margin: 5px; background-color: #fff; border: 2px solid #FFB300; border-radius: 5px; font-weight: bold; color: #333; }
    .section-header { font-size: 1.4em; font-weight: bold; margin: 25px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; color: #333; }
    </style>
""", unsafe_allow_html=True)

# 🌟 [오류 수정 완료] 워드클라우드 생성 함수
def create_cleaned_wc(text_data, height=600):
    if isinstance(text_data, pd.Series): text_list = text_data.dropna().astype(str).tolist()
    else: text_list = text_data
    full_text = " ".join(text_list)
    if not full_text.strip(): return None, None
    stop_words = ["뉴스", "제목", "기자", "통해", "대한", "관련", "위해", "있는", "지난", "이번"]
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=height, background_color='white', colormap='tab10', stopwords=set(stop_words), regexp=r"[가-힣]{2,}", max_words=80).generate(full_text)
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    img_buf = BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    return fig, img_buf

def get_failsafe_keywords(titles):
    try:
        resp = ai_engine.generate_content(f"{titles}에서 제안용 핵심 명사 5개만 #단어로 뽑아줘. 이슈/트렌드 단어 제외.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass

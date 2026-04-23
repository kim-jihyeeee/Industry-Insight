import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai
from collections import Counter

# 1. 설정 및 AI 초기화
st.set_page_config(page_title="AE Total Tool v21.3", layout="wide")
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash-latest')
    except: return None

ai_engine = init_ai()

@st.cache_data
def load_font():
    try:
        res = requests.get("https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf")
        with open("nanum_font.ttf", "wb") as f: f.write(res.content)
        return "nanum_font.ttf"
    except: return None

F_PATH = load_font()

# 🌟 카테고리 설정 (네이버 쇼핑 인사이트 기준 풀세팅)
CATS = {
    "패션의류": ["여성의류", "남성의류", "스포츠의류", "언더웨어/잠옷", "아동의류"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계", "선글라스/안경테", "지갑/벨트"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "이미용가전", "PC/노트북", "음향기기"],
    "식품": ["건강식품", "다이어트식품", "음료", "신선식품", "가공식품", "커피/차", "과자/베이커리"],
    "스포츠/레저": ["골프", "캠핑", "피트니스", "등산", "낚시", "자전거", "수영"],
    "생활/건강": ["주방용품", "욕실용품", "반려동물", "의료기기", "생활용품", "세탁용품"],
    "출산/육아": ["분유/기저귀", "수유용품", "유모차/카시트", "아기물티슈", "임부복/용품"]
}

if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

def fix_columns(df):
    mapping = {
        '날짜': ['날짜', '일자', 'Date', '등록일', '등록일시'],
        '광고주명': ['광고주명', '광고주', '업체명', '업체', 'Client'],
        '소통내용': ['소통내용', '내용', '상담내용', '소통', '상세내용']
    }
    new_cols = {}
    for standard, variations in mapping.items():
        for col in df.columns:
            if col.strip() in variations: new_cols[col] = standard
    return df.rename(columns=new_cols)

# 🌟 워드클라우드 (노이즈 필터링 대폭 강화)
def create_wc(data, h=500):
    txt = " ".join(data.dropna().astype(str)) if isinstance(data, pd.Series) else " ".join(data)
    if not txt.strip(): return None, None
    sw = ["뉴스", "제목", "기자", "통해", "대한", "관련", "위해", "있는", "지난", "이번", "제공", "사진", "오전", "오후", "오늘", "내일", "최근", "대해", "따라", "포함", "그동안", "만큼", "다양한", "상태", "경우"]
    wc = WordCloud(font_path=F_PATH, width=1200, height=h, background_color='white', colormap='tab10', stopwords=set(sw), regexp=r"[가-힣]{2,}", max_words=60).generate(txt)
    fig, ax = plt.subplots(figsize=(15, h/100)); ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    buf = BytesIO(); fig.savefig(buf, format='png', bbox_inches='tight')
    return fig, buf

def get_tags(titles):
    try:
        resp = ai_engine.generate_content(f"{titles}에서 실무 제안용 핵심 단어 5개만 #단어로 뽑아줘.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass
    words = re.findall(r'[가-힣]{2,}', " ".join(titles))
    return [f"#{w}" for w, c in Counter(words).most_common(5)]

# --- 사이드바 ---
menu = st.sidebar.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 직접

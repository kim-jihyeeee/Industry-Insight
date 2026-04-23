import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
import numpy as np
import random
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v2.4", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')
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

# 카테고리 구성 (네이버 데이터랩 기준)
NAVER_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "캐주얼", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "지갑/벨트", "시계/쥬얼리", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "모바일/PC", "영상/음향가전"],
    "식품": ["농/수/축산물", "반찬/가공식품", "음료", "과자/베이커리", "건강식품"],
    "스포츠/레저": ["골프", "캠핑/낚시", "등산", "헬스/요가", "수영/스포츠의류"],
    "가구/인테리어": ["침실/거실가구", "주방가구", "인테리어소품", "침구/커튼"],
    "생활/건강": ["주방/욕실용품", "세탁/생활용품", "반려동물", "의료기기/건강용품"]
}

if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F0F7FF; border-radius: 15px; border-left: 8px solid #007BFF; margin-bottom: 20px; line-height: 1.8; color: #333; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 Industry Insight v2.4")
    main_menu = st.radio("메뉴 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"])

# 🌟 [핵심] 마인드맵 스타일 시각화 함수 (선 연결형 구조)
def draw_mindmap(keywords, center_node):
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_facecolor('white')
    
    # 중복 제거 및 키워드 추출
    unique_words = list(dict.fromkeys(keywords))[:20] # 상위 20개만 사용
    
    # 중앙 노드 (메인 주제)
    ax.annotate(center_node, xy=(0.5, 0.5), xytext=(0.5, 0.5),
                bbox=dict(boxstyle="round,pad=0.8", fc="#FFB300", ec="none", alpha=1),
                fontsize=22, fontweight='bold', color='white', ha='center', va='center', zorder=10)
    
    # 주변 가지 노드 배치
    num_words = len(unique_words)
    radius = 0.38
    for i, word in enumerate(unique_words):
        angle = 2 * np.pi * i / num_words
        x = 0.5 + radius * np.cos(angle)
        y = 0.5 + radius * np.sin(angle)
        
        # 중앙과 키워드를 잇는 가지 선
        ax.plot([0.5, x], [0.5, y], color='#D1D1D1', lw=2, linestyle='-', zorder=1)
        
        # 키워드 박스
        ax.annotate(word, xy=(x, y), xytext=(x, y),
                    bbox=dict(boxstyle="round,pad=0.4", fc="#FFFFFF", ec="#007BFF", lw=1.5, alpha=0.9),
                    fontsize=13, fontweight='bold', color='#333333', ha='center', va='center', zorder=5)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    return fig

# --- [기능 1: 업종별 트렌드 분석] ---
if main_menu == "업종별 트렌드 분석":
    st.header("📈 업종 트렌드 마인드맵 분석")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류 선택", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("중분류 선택", NAVER_CATEGORIES[m_cat])
    period = st.select_slider("분석 기간", options=["3일", "7일", "한달", "60일", "분기"], value="60일")
    
    if st.button(f"🚀 {s_cat} 마인드맵 분석 시작"):
        with st.spinner("최신 이슈를 분석하고 마인드맵을 구성 중입니다..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss); titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:15]]
            
            # 핵심 단어 정제
            words_pool = []
            for t in titles:
                cleaned = re.sub(r'[^\w\s]', '', t)
                words_pool.extend([w for w in cleaned.split() if len(w) > 1 and w not in [s_cat, "이슈", "트렌드"]])
            
            if words_pool:
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"AE 관점에서 {s_cat} 업계 최신 트렌드 {titles}를 기반으로 전략을 제안해줘.")
                        st.markdown(f'<div class="ai-report-card"><b>🤖 {s_cat} 전략 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: pass
                
                # 마인드맵 출력
                fig = draw_mindmap(words_pool, s_cat)
                st.pyplot(fig)

# --- [기능 2: 가망 광고주 제안 솔루션] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 가망 광고주 맞춤 제안")
    t_url = st.text_input("분석할 가망 광고주 URL", placeholder="https://...")
    cc1, cc2 = st.columns(2)
    with cc1: pm_cat = st.selectbox("대분류", list(NAVER_CATEGORIES.keys()), key="pro_m")
    with cc2: ps_cat = st.selectbox("중분류", NAVER_CATEGORIES[pm_cat], key="pro_s")
    
    if st.button("💡 전략 제안서 생성"):
        if not t_url: st.warning("URL을 입력하세요.")
        else:
            with st.spinner("AI가 브랜드 전략을 수립 중입니다..."):
                brand = re.sub(r'https?://|www\.|brand\.naver\.com/|\.com|\.co\.kr|/', '', t_url)
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"광고주 {brand}, 업종 {ps_cat}에 대한 제안서를 작성해줘.")
                        st.markdown(f'<div class="ai-report-card">{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 분석 중입니다. 다시 시도해 주세요.")

# --- [기능 3: DB 관리] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 관리")
    up_f = st.file_uploader("💾 백업 데이터 업로드 (XLSX)", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        rename_map = {'업체명': '광고주명', '광고주': '광고주명', '내용': '소통내용'}
        df.columns = [rename_map.get(c, c) for c in df.columns]
        st.session_state.history_db = df
        st.success("데이터 복구 완료!")
    st.divider()
    search = st.text_input("🔍 광고주 검색")
    d_df = st.session_state.history_db.copy()
    if search: d_df = d_df[d_df['광고주명'].str.contains(search, na=False, case=False)]
    st.dataframe(d_df, use_container_width=True)

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 마인드맵")
    if not st.session_state.history_db.empty:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].dropna().unique()))
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f_df.empty:
            text = " ".join(f_df['소통내용'].fillna('').astype(str))
            words = [w for w in text.split() if len(w) > 1]
            fig = draw_mindmap(words, target)
            st.pyplot(fig)

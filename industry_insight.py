import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
import numpy as np
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v2.5", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        # NotFound 에러 방지를 위해 최신 경로 모델 사용
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')
    except: return None

ai_engine = init_ai()

@st.cache_data
def load_font():
    try:
        # 한글 깨짐 방지를 위해 나눔고딕 폰트 다운로드
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
    .ai-report-card { padding: 25px; background-color: #F8F9FA; border-radius: 15px; border-left: 10px solid #FFB300; margin-bottom: 20px; line-height: 1.8; color: #333; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 Industry Insight v2.5")
    main_menu = st.radio("메뉴 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"])

# 🌟 가독성 중심 워드클라우드 함수
def create_styled_wc(text, font_path):
    wc = WordCloud(
        font_path=font_path,
        width=1200, height=700,
        background_color='white',
        colormap='plasma', # 가독성 좋은 진한 컬러 조합
        prefer_horizontal=0.8,
        max_words=100,
        relative_scaling=0.5
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    return fig

# --- [기능 1: 업종별 트렌드 분석] ---
if main_menu == "업종별 트렌드 분석":
    st.header("📈 업종별 트렌드 리포트")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류 선택", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("중분류 선택", NAVER_CATEGORIES[m_cat])
    period = st.select_slider("분석 기간", options=["3일", "7일", "한달", "60일", "분기"], value="60일")
    
    if st.button(f"🚀 {s_cat} 분석 시작"):
        with st.spinner("최신 트렌드 분석 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss); titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:20]]
            
            if titles:
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"AE 관점에서 {s_cat} 업계 최신 트렌드 {titles}를 요약하고 전략을 제안해줘.")
                        st.markdown(f'<div class="ai-report-card"><b>🤖 {s_cat} 전략 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: pass
                
                fig = create_styled_wc(" ".join(titles), FONT_PATH)
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 이미지 저장", buf.getvalue(), f"{s_cat}_트렌드.png", "image/png")

# --- [기능 2: 가망 광고주 제안 솔루션] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 가망 광고주 맞춤 제안")
    t_url = st.text_input("가망 광고주 URL", placeholder="https://...")
    cc1, cc2 = st.columns(2)
    with cc1: pm_cat = st.selectbox("대분류", list(NAVER_CATEGORIES.keys()), key="pro_m")
    with cc2: ps_cat = st.selectbox("중분류", NAVER_CATEGORIES[pm_cat], key="pro_s")
    
    if st.button("💡 제안서 생성"):
        if not t_url: st.warning("URL을 입력하세요.")
        else:
            with st.spinner("AI가 브랜드 정보를 분석 중입니다..."):
                brand = re.sub(r'https?://|www\.|brand\.naver\.com/|\.com|\.co\.kr|/', '', t_url)
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"광고주 {brand}, 업종 {ps_cat} 제안서 작성해줘.")
                        st.markdown(f'<div class="ai-report-card"><b>💡 {brand} 제안 솔루션</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 분석 중 오류가 발생했습니다.")

# --- [기능 3: DB 관리] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 통합 관리")
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
    st.header("📊 광고주 소통 키워드 분석")
    if not st.session_state.history_db.empty:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].dropna().unique()))
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f_df.empty:
            text = " ".join(f_df['소통내용'].fillna('').astype(str))
            fig = create_styled_wc(text, FONT_PATH)
            st.pyplot(fig)
            buf = BytesIO(); fig.savefig(buf, format="png")
            st.download_button("📥 이미지 저장", buf.getvalue(), f"{target}_소통분석.png", "image/png")

import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v1.0", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"
@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
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

# 세션 초기화
if 'client_db' not in st.session_state: st.session_state.client_db = pd.DataFrame()
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# 2. UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F0F7FF; border-radius: 12px; border-left: 10px solid #007BFF; margin-bottom: 25px; line-height: 1.8; color: #333; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 구성
with st.sidebar:
    st.title("🚀 Industry Insight v1.0")
    st.markdown('<p class="menu-header">📋 기존 광고주 관리 (v12.3)</p>', unsafe_allow_html=True)
    m_int = st.radio("항목", ["광고주 DB/이력 관리", "소통 키워드 분석"], label_visibility="collapsed")
    
    st.markdown('<p class="menu-header">🎯 업계/가망 광고주 분석</p>', unsafe_allow_html=True)
    m_ext = st.radio("항목 ", ["업종별 트렌드 체크", "가망 광고주 제안 솔루션"], label_visibility="collapsed")

# 메뉴 로직 통합
if m_ext == "업종별 트렌드 체크": menu = "trend"
elif m_ext == "가망 광고주 제안 솔루션": menu = "prospect"
else: menu = m_int

# --- [기능 1: 업종별 트렌드 체크] ---
if menu == "trend":
    st.header("📈 업계 이슈/트렌드 체크")
    c1, c2 = st.columns([2, 1])
    with c1: category = st.selectbox("업종 카테고리", ["건강기능식품", "뷰티/코스메틱", "골프/스포츠", "F&B/식음료", "패션/잡화", "IT/가전", "직접 입력"])
    if category == "직접 입력": cat_kw = st.text_input("분석 키워드")
    else: cat_kw = category
    
    with c2: period = st.selectbox("분석 기간", ["최근 3일", "최근 7일", "최근 한달", "최근 60일", "분기(90일)"])
    
    if st.button(f"🚀 {cat_kw} 트렌드 분석 시작"):
        with st.spinner("최신 트렌드 수집 중..."):
            rss = f"https://news.google.com/rss/search?q={cat_kw}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            items = BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:15]
            titles = [i.title.get_text() for i in items]
            
            if titles:
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"AE 관점에서 '{cat_kw}' 업종 트렌드 요약 및 소통 전략 제안:\n" + "\n".join(titles))
                        st.markdown(f'<div class="ai-report-card"><b>🤖 {cat_kw} 업계 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 연동 오류")
                
                wc = WordCloud(font_path=FONT_PATH, width=900, height=400, background_color='white').generate(" ".join(titles))
                fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 이미지 저장", buf.getvalue(), f"{cat_kw}_트렌드.png", "image/png")

# --- [기능 2: 가망 광고주 분석] ---
elif menu == "prospect":
    st.header("🎯 가망 광고주 제안 솔루션")
    target_url = st.text_input("가망 광고주 사이트 URL 또는 브랜드명")
    if st.button("💡 전략 제안 생성"):
        with st.spinner("광고주 맞춤 전략 구상 중..."):
            rss = f"https://news.google.com/rss/search?q={target_url}&hl=ko&gl=KR&ceid=KR:ko"
            items = BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:10]
            context = [i.title.get_text() for i in items]
            if ai_engine:
                try:
                    resp = ai_engine.generate_content(f"광고주 '{target_url}'에 대한 상황 분석 및 제안 방향 제안:\n" + "\n".join(context))
                    st.markdown(f'<div class="ai-report-card"><b>💡 가망 광고주 제안 가이드</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                except: st.error("AI 연동 오류")

# --- [기능 3: 기존 v12.3 기능 유지] ---
elif menu == "광고주 DB/이력 관리":
    st.header("📂 광고주 데이터 관리")
    up_c = st.file_uploader("🏢 광고주 리스트", type=['xlsx', 'csv'])
    if up_c:
        df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
        st.session_state.client_db = df
        st.success("✅ 로드 완료")
    up_h = st.file_uploader("💾 히스토리 복구", type=['xlsx'])
    if up_h:
        st.session_state.history_db = pd.read_excel(up_h)
        st.success("✅ 복구 완료")

elif menu == "소통 키워드 분석":
    st.header("📊 내부 소통 키워드 분석")
    if st.session_state.history_db.empty: st.info("기록이 없습니다.")
    else:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f_df.empty:
            words = f_df['핵심키워드'].fillna('').str.cat(sep=' ') + f_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white').generate(words)
            fig, ax = plt.subplots(); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
            buf = BytesIO(); fig.savefig(buf, format="png")
            st.download_button("📥 이미지 다운로드", buf.getvalue(), f"{target}_분석.png", "image/png")

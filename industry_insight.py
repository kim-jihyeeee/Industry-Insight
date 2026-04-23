import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v1.3", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정 (가장 호환성 높은 모델명으로 고정)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        # 🌟 v1beta 환경에서도 에러 없이 작동하는 가장 확실한 모델 명칭입니다.
        return genai.GenerativeModel('gemini-pro')
    except:
        return None

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

# 세션 초기화 (데이터 누락 방지)
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

# 3. 사이드바 구성 (메뉴 구조를 명확히 분리)
with st.sidebar:
    st.title("🚀 Industry Insight v1.3")
    st.markdown('<p class="menu-header">📋 메뉴 선택</p>', unsafe_allow_html=True)
    # 메뉴를 하나로 통합하여 선택 시 화면이 바로 바뀌도록 수정
    main_menu = st.radio("항목 선택", 
        ["업종별 트렌드 체크", "가망 광고주 제안 솔루션", "광고주 DB/이력 관리", "소통 키워드 분석"],
        label_visibility="collapsed")

# --- [기능 1: 업종별 트렌드 체크] ---
if main_menu == "업종별 트렌드 체크":
    st.header("📈 업종별 이슈/트렌드 체크")
    c1, c2 = st.columns([2, 1])
    with c1: category = st.selectbox("업종 카테고리", ["건강기능식품", "뷰티/코스메틱", "골프/스포츠", "F&B/식음료", "패션/잡화", "IT/가전", "직접 입력"])
    if category == "직접 입력": cat_kw = st.text_input("분석 키워드 입력")
    else: cat_kw = category
    with c2: period = st.selectbox("분석 기간", ["최근 3일", "최근 7일", "최근 한달", "최근 60일", "분기(90일)"])
    
    if st.button(f"🚀 {cat_kw} 트렌드 분석 시작"):
        with st.spinner("AI가 최신 데이터를 분석 중입니다..."):
            rss = f"https://news.google.com/rss/search?q={cat_kw}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss)
            items = BeautifulSoup(res.text, 'xml').find_all('item')[:15]
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in items]
            
            if titles:
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"AE 관점에서 '{cat_kw}' 업계 트렌드 요약 및 제안전략:\n" + "\n".join(titles))
                        st.markdown(f'<div class="ai-report-card"><b>🤖 {cat_kw} 업계 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except Exception as e: st.error(f"AI 응답 실패: {e}")
                
                wc = WordCloud(font_path=FONT_PATH, width=900, height=450, background_color='white').generate(" ".join(titles))
                fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 이미지 저장", buf.getvalue(), f"{cat_kw}_트렌드.png", "image/png")

# --- [기능 2: 가망 광고주 분석] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 가망 광고주 제안 솔루션")
    target = st.text_input("가망 광고주 브랜드명 입력")
    if st.button("💡 전략 제안 생성"):
        with st.spinner(f"'{target}' 전략 수립 중..."):
            rss = f"https://news.google.com/rss/search?q={target}&hl=ko&gl=KR&ceid=KR:ko"
            items = BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:10]
            context = [i.title.get_text() for i in items]
            if ai_engine:
                try:
                    resp = ai_engine.generate_content(f"광고주 '{target}' 현황 분석 및 추천 제안 방향:\n" + "\n".join(context))
                    st.markdown(f'<div class="ai-report-card"><b>💡 제안 솔루션 가이드</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                except Exception as e: st.error(f"AI 분석 실패: {e}")

# --- [기능 3: 광고주 DB 관리 (부활)] ---
elif main_menu == "광고주 DB/이력 관리":
    st.header("📂 광고주 데이터 관리")
    c1, c2 = st.columns(2)
    with c1: 
        up_c = st.file_uploader("🏢 광고주 리스트 업로드 (CSV/XLSX)", type=['xlsx', 'csv'])
        if up_c:
            df = pd.read_csv(up_c) if up_c.name.endswith('.csv') else pd.read_excel(up_c)
            st.session_state.client_db = df
            st.success("✅ 광고주 리스트 로드 완료!")
    with c2:
        up_h = st.file_uploader("💾 소통 이력 복구 (XLSX)", type=['xlsx'])
        if up_h:
            st.session_state.history_db = pd.read_excel(up_h)
            st.success("✅ 히스토리 데이터 복구 완료!")
    
    if not st.session_state.client_db.empty:
        st.divider()
        st.subheader("현재 등록된 광고주 데이터")
        st.dataframe(st.session_state.client_db, use_container_width=True)

# --- [기능 4: 소통 키워드 분석 (부활)] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 내부 소통 키워드 분석")
    if st.session_state.history_db.empty: 
        st.warning("먼저 '광고주 DB/이력 관리' 메뉴에서 이력 파일을 업로드해 주세요.")
    else:
        target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].unique()))
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f_df.empty:
            words = f_df['핵심키워드'].fillna('').str.cat(sep=' ') + f_df['소통내용'].fillna('').str.cat(sep=' ')
            wc = WordCloud(font_path=FONT_PATH, width=900, height=500, background_color='white').generate(words)
            fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
            buf = BytesIO(); fig.savefig(buf, format="png")
            st.download_button("📥 이미지 다운로드", buf.getvalue(), f"{target}_분석.png", "image/png")

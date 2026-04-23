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
st.set_page_config(page_title="AE Industry Insight v2.2", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정 (NotFound 에러 해결을 위한 최신 경로 적용)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        # 🌟 'models/' 명칭을 포함한 최신 경로로 고정하여 에러를 차단합니다.
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')
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

# 네이버 데이터랩 기준 카테고리 구성
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
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 Industry Insight v2.2")
    st.markdown('<p class="menu-header">📋 메인 메뉴</p>', unsafe_allow_html=True)
    main_menu = st.radio("항목 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"], label_visibility="collapsed")

# 마인드맵 시각화 함수 (원형 집중 구조)
def create_mindmap(text, font_path):
    x, y = np.ogrid[:1000, :1000]
    mask = (x - 500) ** 2 + (y - 500) ** 2 > 430 ** 2
    mask = 255 * mask.astype(int)
    wc = WordCloud(font_path=font_path, width=1000, height=1000, background_color='white', mask=mask, colormap='tab10', prefer_horizontal=0.5, relative_scaling=0.6).generate(text)
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- [기능 1: 업종별 트렌드 분석] ---
if main_menu == "업종별 트렌드 분석":
    st.header("📈 네이버 데이터랩 기준 트렌드 분석")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류 선택", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("중분류 선택", NAVER_CATEGORIES[m_cat])
    
    # 🌟 사라졌던 기간 선택 슬라이더 부활
    period_label = st.select_slider("분석 기간 설정", options=["3일", "7일", "한달", "60일", "분기(90일)"], value="60일")
    
    if st.button(f"🚀 {s_cat} 마인드맵 분석 시작"):
        with st.spinner(f"{s_cat} 최신 데이터 분석 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss); titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:15]]
            if titles:
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"전문 AE로서 {s_cat} 업계 최신 트렌드 {titles}를 기반으로 {period_label} 동안의 마케팅 전략을 제안해줘.")
                        st.markdown(f'<div class="ai-report-card"><b>🤖 {s_cat} ({period_label}) 트렌드 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 연동에 일시적인 지연이 발생했습니다. 잠시 후 다시 시도해 주세요.")
                
                fig = create_mindmap(" ".join(titles), FONT_PATH)
                st.pyplot(fig)
                # 🌟 이미지 저장 기능 부활
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 분석 결과 저장 (PNG)", buf.getvalue(), f"{s_cat}_트렌드.png", "image/png")

# --- [기능 2: 가망 광고주 분석] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 URL 기반 가망 광고주 맞춤 제안")
    t_url = st.text_input("가망 광고주 URL 입력", placeholder="https://...")
    cc1, cc2 = st.columns(2)
    with cc1: pm_cat = st.selectbox("대분류 선택", list(NAVER_CATEGORIES.keys()), key="p_m")
    with cc2: ps_cat = st.selectbox("중분류 선택", NAVER_CATEGORIES[pm_cat], key="p_s")
    
    if st.button("💡 제안서 초안 생성"):
        if not t_url: st.warning("URL을 입력해 주세요.")
        else:
            with st.spinner("브랜드 현황 및 시장 데이터 매칭 중..."):
                brand = re.sub(r'https?://|www\.|brand\.naver\.com/|\.com|\.co\.kr|/', '', t_url)
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"광고주 {brand}, 업종 {ps_cat}. AE 관점에서 1.현황분석 2.트렌드전략 3.추천매체를 상세히 제안해줘.")
                        st.markdown(f'<div class="ai-report-card"><b>💡 {brand} 맞춤 제안 솔루션</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 분석 중 오류가 발생했습니다.")

# --- [기능 3: DB 관리] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 통합 관리 및 검색")
    with st.expander("💾 백업 데이터 복구 (XLSX)"):
        up_f = st.file_uploader("파일 업로드", type=['xlsx'])
        if up_f:
            df = pd.read_excel(up_f, engine='openpyxl')
            rename_map = {'업체명': '광고주명', '광고주': '광고주명', '내용': '소통내용'}
            df.columns = [rename_map.get(c, c) for c in df.columns]
            st.session_state.history_db = df[['날짜', '광고주명', '소통내용', '핵심키워드']]
            st.success("✅ 로드 완료!")
    st.divider()
    query = st.text_input("🔍 광고주 실시간 검색 (업체명 입력)")
    d_df = st.session_state.history_db.copy()
    if query: d_df = d_df[d_df['광고주명'].str.contains(query, na=False, case=False)]
    st.dataframe(d_df, use_container_width=True)

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 마인드맵")
    if st.session_state.history_db.empty:
        st.info("데이터를 먼저 로드해 주세요.")
    else:
        clients = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
        target = st.selectbox("분석할 광고주 검색/선택", clients)
        period = st.select_slider("분석 범위(일)", options=[7, 30, 90, 180, 365], value=90)
        
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f_df.empty:
            text = " ".join(f_df['소통내용'].fillna('').astype(str))
            if len(text.strip()) > 5:
                fig = create_mindmap(text, FONT_PATH)
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 마인드맵 이미지 저장", buf.getvalue(), f"{target}_소통분석.png", "image/png")

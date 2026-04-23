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
st.set_page_config(page_title="AE Industry Insight v2.0", layout="wide", initial_sidebar_state="auto")

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

# 🌟 [공통] 네이버 데이터랩 기준 상세 카테고리 데이터
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

# 세션 초기화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F8F9FA; border-radius: 15px; border-left: 10px solid #FFB300; margin-bottom: 25px; line-height: 1.8; color: #333; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 Industry Insight v2.0")
    st.markdown('<p class="menu-header">📋 메인 메뉴</p>', unsafe_allow_html=True)
    main_menu = st.radio("항목 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"], label_visibility="collapsed")

# 마인드맵 시각화 함수
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
    
    if st.button(f"🚀 {s_cat} 마인드맵 분석 시작"):
        with st.spinner("최신 이슈 분석 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss); titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:15]]
            if titles:
                if ai_engine:
                    resp = ai_engine.generate_content(f"AE 관점에서 {s_cat} 업계 최신 트렌드 {titles}를 기반으로 캠페인 제안 전략을 써줘.")
                    st.markdown(f'<div class="ai-report-card"><b>🤖 {s_cat} 분석 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                fig = create_mindmap(" ".join(titles), FONT_PATH)
                st.pyplot(fig)

# --- [기능 2: 가망 광고주 제안 솔루션 (카테고리 통합)] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 URL 기반 가망 광고주 맞춤 제안")
    t_url = st.text_input("가망 광고주 URL 입력", placeholder="https://brand.naver.com/...")
    
    # 🌟 트렌드 분석과 동일한 카테고리 선택 UI
    st.write("---")
    st.markdown("##### 🔍 분석 업종 설정 (네이버 데이터랩 기준)")
    cc1, cc2 = st.columns(2)
    with cc1: target_m_cat = st.selectbox("대분류 선택", list(NAVER_CATEGORIES.keys()), key="prospect_m")
    with cc2: target_s_cat = st.selectbox("중분류 선택", NAVER_CATEGORIES[target_m_cat], key="prospect_s")
    
    if st.button("💡 제안 전략 및 매체 믹스 생성"):
        if not t_url: st.warning("URL을 입력해 주세요.")
        else:
            with st.spinner(f"'{target_s_cat}' 시장 트렌드와 브랜드 정보를 매칭 중..."):
                # URL에서 브랜드명 추측
                brand_guess = t_url.split("//")[-1].split(".")[0]
                if "naver" in brand_guess: brand_guess = t_url.split("/")[-1]
                
                # 해당 카테고리 최신 이슈 수집
                rss = f"https://news.google.com/rss/search?q={target_s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
                titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:10]]
                
                if ai_engine:
                    prompt = f"광고주: {brand_guess}({t_url})\n카테고리: {target_m_cat} > {target_s_cat}\n시장 트렌드: {titles}\n\n위 정보를 바탕으로 전문 AE로서 1.브랜드 페인포인트 2.업종 트렌드 연계 전략 3.추천 매체 믹스 제안서를 작성해줘."
                    try:
                        resp = ai_engine.generate_content(prompt)
                        st.markdown(f'<div class="ai-report-card"><b>💡 {brand_guess} 맞춤 제안 솔루션</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 분석 중 오류가 발생했습니다.")

# --- [기능 3: DB 관리] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 광고주 데이터 통합 관리")
    
    with st.expander("💾 백업 파일 복구"):
        up_f = st.file_uploader("XLSX 파일을 업로드하세요", type=['xlsx'])
        if up_f:
            df = pd.read_excel(up_f, engine='openpyxl')
            rename_map = {'업체명': '광고주명', '광고주': '광고주명', '내용': '소통내용'}
            df.columns = [rename_map.get(c, c) for c in df.columns]
            st.session_state.history_db = df[['날짜', '광고주명', '소통내용', '핵심키워드']]
            st.success("✅ 복구 완료!")

    with st.expander("📝 소통 기록 추가"):
        with st.form("add_log", clear_on_submit=True):
            col1, col2 = st.columns(2)
            c_name = col1.text_input("광고주명")
            c_date = col2.date_input("날짜", datetime.date.today())
            c_content = st.text_area("내용")
            if st.form_submit_button("💾 저장"):
                if c_name:
                    new_row = pd.DataFrame([[c_date, c_name, c_content, ""]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                    st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
                    st.success("저장 완료!")

    st.divider()
    st.subheader("🔍 광고주 통합 검색")
    query = st.text_input("업체명 검색 (실시간 필터링)")
    d_df = st.session_state.history_db.copy()
    if query: d_df = d_df[d_df['광고주명'].str.contains(query, na=False, case=False)]
    st.dataframe(d_df, use_container_width=True)

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 키워드 분석")
    if st.session_state.history_db.empty:
        st.info("데이터를 먼저 로드해 주세요.")
    else:
        clients = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
        target = st.selectbox("분석할 광고주 검색/선택", clients)
        period = st.select_slider("분석 기간", options=[7, 30, 90, 180, 365], value=90)
        
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if not f_df.empty:
            text = " ".join(f_df['소통내용'].fillna('').astype(str))
            if len(text.strip()) > 5:
                fig = create_mindmap(text, FONT_PATH)
                st.pyplot(fig)

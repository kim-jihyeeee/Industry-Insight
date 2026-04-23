import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v1.4", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정 (호환성 높은 모델명 사용)
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('gemini-pro')
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

# 2. 네이버 데이터랩 기준 상세 카테고리 구성
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
if 'history_db' not in st.session_state: st.session_state.history_db = pd.DataFrame()

# 3. UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F8F9FA; border-radius: 12px; border-left: 10px solid #FFB300; margin-bottom: 25px; line-height: 1.8; color: #333; }
    .menu-header { font-size: 1.1em; font-weight: bold; color: #FFB300; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# 4. 사이드바 메뉴
with st.sidebar:
    st.title("🚀 Industry Insight v1.4")
    st.markdown('<p class="menu-header">📋 메뉴 선택</p>', unsafe_allow_html=True)
    main_menu = st.radio("항목 선택", ["업종별 트렌드 체크", "가망 광고주 분석/제안", "광고주 DB 관리"], label_visibility="collapsed")

# --- [기능 1: 업종별 트렌드 체크] ---
if main_menu == "업종별 트렌드 체크":
    st.header("📈 업종별 이슈 마인드맵 분석")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류 (네이버 데이터랩 기준)", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("상세 카테고리", NAVER_CATEGORIES[m_cat])
    
    period = st.select_slider("분석 기간 설정", options=["3일", "7일", "30일", "60일", "90일"], value="60일")
    
    if st.button(f"🚀 {s_cat} 시장 마인드맵 분석 시작"):
        with st.spinner(f"{s_cat} 최신 데이터 수집 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:20]]
            
            if titles:
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"당신은 전문 AE입니다. {s_cat} 카테고리의 최신 이슈들을 분석하고, 브랜드가 활용할 마케팅 인사이트 3가지를 제안하세요:\n" + "\n".join(titles))
                        st.markdown(f'<div class="ai-report-card"><b>🤖 {s_cat} 전략 인사이트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 분석 중 오류가 발생했습니다.")
                
                # 마인드맵 스타일 시각화 (중앙 집중형 워드클라우드)
                wc = WordCloud(font_path=FONT_PATH, width=1000, height=600, background_color='white', 
                               colormap='tab10', prefer_horizontal=0.8, relative_scaling=0.5).generate(" ".join(titles))
                fig, ax = plt.subplots(figsize=(12, 7)); ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 마인드맵 이미지 저장", buf.getvalue(), f"{s_cat}_트렌드_마인드맵.png", "image/png")

# --- [기능 2: 가망 광고주 분석/제안 (URL 기반)] ---
elif main_menu == "가망 광고주 분석/제안":
    st.header("🎯 URL 기반 가망 광고주 맞춤 전략")
    c_url, c_cat = st.columns([2, 1])
    with c_url: target_url = st.text_input("가망 광고주 URL (공식몰/홈페이지)", placeholder="https://brand.naver.com/...")
    with c_cat: cat_match = st.selectbox("매칭 카테고리 설정", [f"{k} > {v}" for k, vv in NAVER_CATEGORIES.items() for v in vv])
    
    if st.button("💡 URL 분석 및 전략 제안서 생성"):
        if not target_url: st.warning("분석할 URL을 입력해 주세요.")
        else:
            with st.spinner("URL 정보를 바탕으로 시장 트렌드와 매칭 중..."):
                # URL에서 브랜드 키워드 추출 시도
                clean_url = target_url.replace("https://","").replace("http://","")
                brand_key = clean_url.split("/")[1] if "brand.naver.com" in clean_url else clean_url.split(".")[0]
                sub_cat_name = cat_match.split(" > ")[1]
                
                rss = f"https://news.google.com/rss/search?q={brand_key}+{sub_cat_name}&hl=ko&gl=KR&ceid=KR:ko"
                news_context = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:12]]
                
                if ai_engine:
                    try:
                        prompt = f"광고주 URL: {target_url}\n업종: {cat_match}\n관련시장 뉴스: {news_context}\n\n위 데이터를 기반으로 1.브랜드 현황 및 시장 위치 2.카테고리 트렌드 연계 전략 3.AE 추천 소구점 및 매체 믹스를 제안서 형식으로 작성해줘."
                        resp = ai_engine.generate_content(prompt)
                        st.markdown(f'<div class="ai-report-card"><b>💡 {brand_key} 맞춤 제안 솔루션</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 분석에 실패했습니다.")

# --- [기능 3: 광고주 DB 관리] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 통합 관리")
    up_f = st.file_uploader("💾 광고주 리스트 및 소통 이력 복구 (XLSX)", type=['xlsx'])
    if up_f:
        st.session_state.history_db = pd.read_excel(up_f)
        st.success("✅ 데이터 로드 완료")
        st.dataframe(st.session_state.history_db, use_container_width=True)

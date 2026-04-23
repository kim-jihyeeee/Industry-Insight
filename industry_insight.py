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
st.set_page_config(page_title="AE Industry Insight v1.8", layout="wide", initial_sidebar_state="auto")

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

# 카테고리 구성 (네이버 데이터랩 기준)
NAVER_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "캐주얼", "언더웨어"],
    "패션잡화": ["신발", "가방", "지갑/벨트", "쥬얼리", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "IT기기"],
    "식품": ["가공식품", "신선식품", "음료", "건강식품"],
    "스포츠/레저": ["골프", "캠핑/낚시", "등산", "피트니스"],
    "생활/건강": ["주방/욕실", "생활용품", "반려동물", "의료기기"]
}

# 세션 초기화 및 데이터 유지 로직
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
    st.title("🚀 Industry Insight v1.8")
    st.markdown('<p class="menu-header">📋 메인 메뉴</p>', unsafe_allow_html=True)
    main_menu = st.radio("항목 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"], label_visibility="collapsed")

# 마인드맵 시각화 함수 (원형 구조)
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
    st.header("📈 업계 이슈 마인드맵 리포트")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("상세 카테고리", NAVER_CATEGORIES[m_cat])
    period_days = st.select_slider("분석 기간 설정", options=["3일", "7일", "한달", "60일", "분기(90일)"], value="60일")
    
    if st.button(f"🚀 {s_cat} 분석 시작"):
        with st.spinner("트렌드 수집 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss); titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:15]]
            if titles:
                if ai_engine:
                    resp = ai_engine.generate_content(f"{s_cat} 업계 최신 트렌드 {titles}를 기반으로 캠페인 제안점을 요약해줘.")
                    st.markdown(f'<div class="ai-report-card"><b>🤖 {s_cat} ({period_days}) 분석 리포트</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                fig = create_mindmap(" ".join(titles), FONT_PATH)
                st.pyplot(fig)

# --- [기능 2: 가망 광고주 제안 솔루션] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 URL 기반 가망 광고주 제안")
    t_url = st.text_input("가망 광고주 URL", placeholder="https://...")
    t_cat = st.selectbox("업종 카테고리", [f"{k} > {v}" for k, vv in NAVER_CATEGORIES.items() for v in vv])
    if st.button("💡 전략 도출"):
        if not t_url: st.warning("URL을 입력하세요.")
        else:
            with st.spinner("브랜드 분석 중..."):
                brand = t_url.split("//")[-1].split(".")[0]
                if ai_engine:
                    resp = ai_engine.generate_content(f"광고주 {brand}, 업종 {t_cat}에 대해 AE가 제안할 페인포인트와 매체 전략을 써줘.")
                    st.markdown(f'<div class="ai-report-card">{resp.text}</div>', unsafe_allow_html=True)

# --- [기능 3: DB 관리 (KeyError 해결)] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 관리 및 복구")
    with st.expander("📝 실시간 소통 기록 입력"):
        with st.form("in_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("광고주명")
            date = col2.date_input("날짜", datetime.date.today())
            content = st.text_area("내용")
            if st.form_submit_button("저장"):
                row = pd.DataFrame([[date, name, content, ""]], columns=['날짜', '광고주명', '소통내용', '핵심키워드'])
                st.session_state.history_db = pd.concat([st.session_state.history_db, row], ignore_index=True)
                st.success("저장 완료!")

    st.divider()
    up_f = st.file_uploader("💾 백업 파일 복구 (XLSX)", type=['xlsx'])
    if up_f:
        try:
            df = pd.read_excel(up_f, engine='openpyxl')
            # 🌟 맵핑 로직: 다양한 컬럼명을 표준명으로 강제 변경
            rename_map = {
                '업체명': '광고주명', '광고주': '광고주명', '브랜드': '광고주명',
                '내용': '소통내용', '피드백': '소통내용', '상세': '소통내용'
            }
            df.columns = [rename_map.get(c, c) for c in df.columns]
            
            # 필수 컬럼 보장
            for col in ['날짜', '광고주명', '소통내용', '핵심키워드']:
                if col not in df.columns: df[col] = ""
            
            st.session_state.history_db = df[['날짜', '광고주명', '소통내용', '핵심키워드']]
            st.success("✅ 데이터 복구 및 동기화 완료!")
        except: st.error("파일 형식이 맞지 않습니다.")
    
    st.dataframe(st.session_state.history_db, use_container_width=True)

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 키워드 마인드맵")
    # history_db가 비어있거나 광고주명 컬럼이 없는 경우 방지
    if st.session_state.history_db.empty or '광고주명' not in st.session_state.history_db.columns:
        st.info("데이터를 먼저 입력하거나 DB 관리 메뉴에서 파일을 업로드해 주세요.")
    else:
        # 데이터 정제 및 유효 광고주 추출
        valid_df = st.session_state.history_db.dropna(subset=['광고주명'])
        clients = sorted(valid_df['광고주명'].unique().tolist())
        
        if not clients:
            st.warning("분석 가능한 광고주 데이터가 없습니다.")
        else:
            target = st.selectbox("분석할 광고주 선택", clients)
            period = st.select_slider("분석 기간 설정", options=[7, 30, 90, 180, 365], value=90)
            
            f_df = valid_df[valid_df['광고주명'] == target]
            if not f_df.empty:
                text = " ".join(f_df['소통내용'].fillna('').astype(str))
                if len(text.strip()) > 5:
                    fig = create_mindmap(text, FONT_PATH)
                    st.pyplot(fig)
                    buf = BytesIO(); fig.savefig(buf, format="png")
                    st.download_button("📥 이미지 저장", buf.getvalue(), f"{target}_소통분석.png", "image/png")
                else: st.warning("분석할 텍스트가 부족합니다.")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# Core Logic & Math (มยผ. 1311-50)
# ==========================================
def calculate_q(V):
    """คำนวณหน่วยแรงลมอ้างอิง q = 0.5 * rho * V^2"""
    rho = 1.25  # ความหนาแน่นอากาศ (kg/m^3)
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665  # แปลงเป็น kgf/m^2

def get_Ce_details(z, exposure):
    """คำนวณ Ce อิงตาม Power Law และคืนค่าวิธีคิดโดยละเอียด"""
    z_eff = max(z, 6.0)  # ต่ำสุด 6 เมตรตาม มยผ.
    if 'A' in exposure:
        alpha = 0.20
        min_val, max_val = 0.9, 1.5
    elif 'B' in exposure:
        alpha = 0.28
        min_val, max_val = 0.7, 1.2
    else:
        alpha = 0.40
        min_val, max_val = 0.5, 1.0
        
    raw_ce = (z_eff / 10.0) ** alpha
    ce = min(max(raw_ce, min_val), max_val)
    
    explanation = f"สูตรภูมิประเทศ {exposure[:1]}: (z_eff/10)^{alpha} = ({z_eff}/10)^{alpha} = {raw_ce:.4f} → ควบคุมด้วยค่าตามมาตรฐานที่ {ce:.3f}"
    if z < 6.0:
        explanation = f"เนื่องจากความสูง z = {z} ม. ต่ำกว่าขั้นต่ำ (6.0 ม.) ให้ใช้ z = 6.0 ม. คำนวณ | " + explanation
        
    return ce, explanation

# ==========================================
# Streamlit UI Setup & Styling
# ==========================================
st.set_page_config(page_title="Wind Load Analyzer | มยผ. 1311-50", layout="wide")

# Custom CSS เพื่อตกแต่งความสวยงามและการจัดหน้า
st.markdown("""
    <style>
    .main-title { font-size: 2.3rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 25px; }
    .section-header { font-size: 1.4rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 15px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    .metric-container { background-color: #F3F4F6; padding: 15px; border-radius: 8px; border-left: 5px solid #3B82F6; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind Load Analyzer & Structural Report</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">โปรแกรมวิเคราะห์แรงลมแยกรายชั้นตามมาตรฐาน มยผ. 1311-50 (ระบบคำนวณเรียบร้อยแบบตอบสนองทันที)</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR: ควบคุมตัวแปรคงที่และสภาพแวดล้อมทั้งหมด
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดและสเปกแรงลม")

st.sidebar.subheader("1. ข้อมูลสถานที่ตั้งอาคาร")
V_input = st.sidebar.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0, help="ความเร็วลมเฉลี่ย 50 ปี ตามจังหวัดที่ตั้งอาคาร")
exposure = st.sidebar.selectbox("สภาพภูมิประเทศ (Exposure Class)", ['A (พื้นที่โล่งแจ้ง/ชายฝั่ง)', 'B (พื้นที่ชานเมือง/มีต้นไม้หนาแน่น)', 'C (ในเมืองใหญ่/ตึกสูงหนาแน่น)'])
Iw_input = st.sidebar.selectbox("ค่าประกอบความสำคัญอาคาร (Iw)", [1.0, 1.15], index=0, help="1.0 = อาคารทั่วไป, 1.15 = อาคารสาธารณะ/โรงพยาบาล/อาคารอพยพ")

st.sidebar.markdown("---")
st.sidebar.subheader("2. สัมประสิทธิ์แรงดันและลักษณะอาคาร")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อมของอาคาร", ["อาคารปิดทึบ (Enclosed Building)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1, help="ปกติใช้ 2.0 สำหรับการออกแบบโครงสร้างหลักอาคารทั่วไป")
Cp_w = st.sidebar.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)

# กำหนดค่า GCpi อัตโนมัติตามประเภทการปิดล้อม
GCpi = 0.55 if "Partially" in enclosure else 0.18

# ==========================================
# MAIN PAGE: ส่วนกรอกมิติอาคารและการแสดงผลหลัก
# ==========================================
st.markdown('<div class="section-header">🏢 มิติรูปทรงและโครงสร้างระดับความสูงอาคาร</div>', unsafe_allow_html=True)

# จัดสรรพื้นที่กรอกสเปกโครงสร้างตึกแนวราบ
col_b, col_l, col_n = st.columns(3)
with col_b:
    B = st.number_input("ความกว้างอาคารแนวขนานลม B (เมตร)", value=15.0, min_value=1.0, step=0.5)
with col_l:
    L = st.number_input("ความยาวอาคารแนวตั้งฉากลม L (เมตร)", value=20.0, min_value=1.0, step=0.5)
with col_n:
    num_stories = st.number_input("จำนวนชั้นของอาคารทั้งหมด (Stories)", value=3, min_value=1, step=1)

# พื้นที่จัดการความสูงแต่ละชั้นแบบไดนามิก (ใช้ Expander เพื่อความสะอาดตา)
with st.expander("📐 คลิกเพื่อปรับแต่งความสูงแยกแต่ละชั้น (กรณีความสูงชั้นไม่เท่ากัน)", expanded=True):
    st.markdown("*ระบบจะสร้างช่องกรอกตามจำนวนชั้นที่คุณเลือกด้านบนอัตโนมัติ:*")
    floor_cols = st.columns(min(num_stories, 4)) # ตัดแบ่งคอลัมน์ไม่ให้ล้นจอ (สูงสุด 4 คอลัมน์ต่อแถว)
    
    floor_heights = []
    for i in range(num_stories):
        col_idx = i % 4
        default_h = 4.0 if i == 0 else 3.5 # ชั้น 1 มักจะสูงกว่าชั้นอื่น
        with floor_cols[col_idx]:
            h_val = st.number_input(f"ความสูงชั้นที่ {i+1} (ม.)", value=default_h, min_value=1.0, step=0.1, key=f"h_f_{i}")
            floor_heights.append(h_val)

# คำนวณความสูงสะสมรวมของอาคาร (H)
H_total = sum(floor_heights)

# ==========================================
# Engine Core Processing (คำนวณเบื้องหลัง)
# ==========================================
q = calculate_q(V_input)
Ce_H, Ce_H_exp = get_Ce_details(H_total, exposure)
qh = q * Ce_H

z_cumulative = 0
floors_data = []

for i in range(num_stories):
    h_current = floor_heights[i]
    z_bottom = z_cumulative
    z_top = z_cumulative + h_current
    z_mid = (z_bottom + z_top) / 2.0 # จุดกึ่งกลางสำหรับรับแรงดันลมประจำชั้น
    
    Ce_mid, Ce_mid_exp = get_Ce_details(z_mid, exposure)
    p_w_z = Iw_input * q * Ce_mid * Cg_input * Cp_w
    
    floors_data.append({
        "floor_num": i + 1,
        "height": h_current,
        "z_bottom": z_bottom,
        "z_top": z_top,
        "z_mid": z_mid,
        "Ce": Ce_mid,
        "Ce_exp": Ce_mid_exp,
        "p_windward": p_w_z
    })
    z_cumulative = z_top

p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_internal_pos = qh * GCpi
p_internal_neg = qh * (-GCpi)

# ==========================================
# TAB NAVIGATION: การนำเสนอผลลัพธ์แยกตามการใช้งาน
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📊 แดชบอร์ดสรุปผลและโมเดลจำลอง", 
    "📑 เล่มรายการคำนวณอย่างละเอียด", 
    "💾 ตารางสรุปโหลดเพื่อการออกแบบ (Design Output)"
])

# ------------------------------------------
# TAB 1: Dashboard & Visual Model
# ------------------------------------------
with tab1:
    # 1.1 แสดงการ์ดตัวเลขสรุปวิศวกรรม (Key Metrics)
    st.markdown("#### 🎯 สรุปผลลัพธ์หลักจากการคำนวณ")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric(label="ความสูงรวมตึก (H)", value=f"{H_total:.2f} m")
    with m_col2:
        st.metric(label="แรงลมอ้างอิงพื้นฐาน (q)", value=f"{q:.2f} kgf/m²")
    with m_col3:
        st.metric(label="แรงลมรับอัดสูงสุด (Max Windward)", value=f"{floors_data[-1]['p_windward']:.1f} kgf/m²")
    with m_col4:
        st.metric(label="แรงลมดูดท้ายตึก (Leeward)", value=f"{abs(p_leeward):.1f} kgf/m²")

    st.markdown("---")
    
    # 1.2 แผนภาพรูปตัดโครงสร้างจำลองอาคารและแรงลม
    st.markdown("#### 📐 แผนภาพแสดงทิศทางและขนาดหน่วยแรงลมออกแบบ")
    
    fig = go.Figure()
    
    # วาดตัวตึกหลัก
    fig.add_trace(go.Scatter(
        x=[0, B, B, 0, 0], 
        y=[0, 0, H_total, H_total, 0], 
        fill="toself", fillcolor="rgba(30, 58, 138, 0.05)",
        line=dict(color="#1E3A8A", width=3), name="โครงสร้างอาคาร"
    ))
    
    # แสดงรายละเอียดเส้นระดับและลูกศรแรงลมตามความสูงจริง
    for f in floors_data:
        # เส้นแสดงระดับความสูงแต่ละชั้น
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'],
                      line=dict(color="rgba(75, 85, 99, 0.3)", width=1.5, dash="dash"))
        # ข้อความบอกความสูงสะสม (ฝั่งขวาอาคาร) - แก้ไขใช้ HTML <b> เพื่อตัวหนา
        fig.add_annotation(x=B + 0.3, y=f['z_top'], text=f"<b>z = {f['z_top']:.2f} m</b>", 
                           showarrow=False, xanchor="left", font=dict(size=11, color="#2563EB"))
        # ชื่อชั้นและความสูงของตัวชั้นเอง (กึ่งกลางโครงสร้าง)
        fig.add_annotation(x=B/2, y=f['z_mid'], text=f"ชั้นที่ {f['floor_num']} (h = {f['height']} ม.)", 
                           showarrow=False, font=dict(size=11, color="#4B5563", italic=True))
        
        # วาดลูกศรหน่วยแรงลมด้านรับลม (Windward) - แก้ไขใช้ HTML <b> เพื่อตัวหนา
        arrow_len = 1.5 + (f['p_windward'] / 40.0) 
        fig.add_annotation(x=0, y=f['z_mid'], ax=-arrow_len, ay=f['z_mid'], xref="x", yref="y", axref="x", ayref="y",
                           text=f"<b>{f['p_windward']:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor="#DC2626",
                           font=dict(color="#DC2626", size=10), xanchor="right")

    # วาดลูกศรแรงลมด้านตามลม (Leeward) - แก้ไขใช้ HTML <b> เพื่อตัวหนา
    fig.add_annotation(x=B + 4.5, y=H_total/2, ax=B, ay=H_total/2, xref="x", yref="y", axref="x", ayref="y",
                       text=f"<b>Leeward Suction<br>{p_leeward:.1f} kgf/m²<br>(คงที่ตลอดแนวความสูง)</b>", showarrow=True, 
                       arrowhead=2, arrowsize=1.2, arrowcolor="#EA580C", font=dict(color="#EA580C", size=11))

    fig.update_layout(
        xaxis_title="ความกว้างของอาคารแนวขนานลม B (เมตร)", 
        yaxis_title="ระดับความสูงวัดจากพื้นดิน z (เมตร)", 
        yaxis_range=[-1, H_total + 2], 
        xaxis_range=[-7, B + 7], 
        height=550,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        plot_bgcolor="white"
    )
    # เพิ่ม Grid ให้กราฟอ่านระยะง่ายขึ้นแบบพิมพ์เขียนวิศวกรรม
    fig.update_xaxes(showgrid=True, gridcolor='#E5E7EB')
    fig.update_yaxes(showgrid=True, gridcolor='#E5E7EB')
    
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# TAB 2: Ultra-Detailed Calculation Report
# ------------------------------------------
with tab2:
    st.markdown("#### 📑 เล่มรายการคำนวณโครงสร้างอย่างเป็นสเต็ป (ส่งตรวจอนุมัติ)")
    
    st.markdown(f"""
    ### **[ส่วนที่ 1]: ข้อกำหนดพื้นฐานและการตั้งต้นโครงสร้าง**
    * มาตรฐานอ้างอิง: **มยผ. 1311-50** (มาตรฐานการคำนวณแรงลมและการตอบสนองของโครงสร้าง)
    * วิธีการออกแบบ: **ระบบโครงสร้างหลักต้านทานแรงลม (MWFRS)** อาคารรูปทรงสี่เหลี่ยมหลังคาแบน
    * มิติสิ่งปลูกสร้างจริง:
      * ความกว้างแนวขนานลม ($B$) = `{B:.2f}` ม. | ความยาวแนวตั้งฉากลม ($L$) = `{L:.2f}` ม.
      * จำนวนชั้นรวม = `{num_stories}` ชั้น | ความสูงสุทธิรวมรวมยอดอาคาร ($H$) = `{H_total:.2f}` ม.
    
    ---
    ### **[ส่วนที่ 2]: ขั้นตอนการคำนวณหน่วยแรงลมอ้างอิง (Velocity Pressure, $q$)**
    คำนวณแรงดันลมสถิตที่สภาวะความหนาแน่นอากาศมาตรฐานแปรผันตามความเร็วลมพื้นที่:
    * สมการหลัก: $$q = \\frac{{0.5 \\cdot \\rho \\cdot V^2}}{{g}}$$
    * แทนค่าตัวแปร:
      * ความเร็วลมพื้นฐานตามพื้นที่ศึกษา ($V$) = `{V_input:.2f}` m/s
      * ความหนาแน่นของมวลอากาศ ($\rho$) = `1.25` $kg/m^3$
      * ค่าเร่งโน้มถ่วงมาตรฐานเพื่อแปลงหน่วยพาสคัล ($g$) = `9.80665` $m/s^2$
    * **แสดงขั้นตอนถอดสมการคณิตศาสตร์:**
      $$q = \\frac{{0.5 \\cdot 1.25 \\cdot ({V_input:.2f})^2}}{{9.80665}}$$
      $$q = \\frac{{0.5 \\cdot 1.25 \\cdot {V_input**2:.2f}}}{{9.80665}} = \\frac{{{0.5 * 1.25 * (V_input**2):.4f}}}{{9.80665}}$$
      $$\\mathbf{{q = {q:.4f} \\text{{ kgf/m}}^2}}$$
    
    ---
    ### **[ส่วนที่ 3]: ค่าสัมประสิทธิ์และตัวคูณประกอบคงที่**
    * ค่าตัวคูณประกอบความสำคัญแรงลม ($I_w$) = `{Iw_input:.2f}`
    * สภาพภูมิประเทศอาคารจัดอยู่ในประเภท = `ประเภท {exposure}`
    * ค่าสัมประสิทธิ์ลมกระโชกแปรปรวน ($C_g$) = `{Cg_input:.2f}`
    * สัมประสิทธิ์แรงดันภายในอาคารสุทธิ ($GC_{{pi}}$) สำหรับระบบ `{enclosure}`:
      * ค่าพิจารณาแรงดันภายในแปรผัน = `±{GCpi:.2f}` *(ต้องคิดรวมทั้งประเภทลมดัน [+] และลมดูด [-])*
    * สัมประสิทธิ์ภายนอกผนังฝั่งตามลม ($C_p \\text{{ Leeward}}$) = `{Cp_l:.2f}`
    * สัมประสิทธิ์ภายนอกผนังฝั่งรับลม ($C_p \\text{{ Windward}}$) = `{Cp_w:.2f}`
    
    ---
    ### **[ส่วนที่ 4]: รายการวิเคราะห์คำนวณหน่วยแรงลมภายนอกด้านรับลม (Windward) แยกรายชั้น**
    สมการพื้นฐาน: $$p_{{ext}} = I_w \\cdot q \\cdot C_e \\cdot C_g \\cdot C_p$$
    *(หมายเหตุ: ค่าสัมประสิทธิ์ประกอบการเปิดโล่ง $C_e$ จะเปลี่ยนไปตามความสูงกึ่งกลางจริงของชั้นนั้นๆ)*
    """)
    
    # แสดงการแทนค่ารายชั้น แก้ไขใช้ st.expander ที่ถูกต้องตามหลัก Streamlit
    for f in floors_data:
        with st.expander(f"🔍 การสับเปลี่ยนตัวเลขและสูตรคำนวณของ: ชั้นที่ {f['floor_num']}", expanded=True):
            st.markdown(f"""
            * **ช่วงพิกัดระดับชั้น:** ตั้งแต่ระดับระดับดินสะสม `+{f['z_bottom']:.2f}` ม. ถึง `+{f['z_top']:.2f}` ม.
            * **ระดับความสูงอ้างอิงกึ่งกลางชั้นเพื่อหาแรงลม ($z_{{mid}}$):** $$z_{{mid}} = \\frac{{{f['z_bottom']:.2f} + {f['z_top']:.2f}}}{{2}} = {f['z_mid']:.2f} \\text{{ เมตร}}$$
            * **การคำนวณสัมประสิทธิ์ความสูงภูมิประเทศ ($C_e$):**
              * วิธีการประมวลผล: {f['Ce_exp']} 
              * สรุปค่าสัมประสิทธิ์ประจำชั้น $C_e$ = **`{f['Ce']:.3f}`**
            * **แทนค่าลงในสมการแรงลมภายนอกประจำชั้น:**
              $$p_w = I_w \\cdot q \\cdot C_e \\cdot C_g \\cdot C_{{p(windward)}}$$
              $$p_w = {Iw_input:.2f} \\cdot {q:.2f} \\cdot {f['Ce']:.3f} \\cdot {Cg_input:.2f} \\cdot {Cp_w:.2f}$$
              $$p_w = {Iw_input * q * f['Ce'] * Cg_input:.4f} \\cdot {Cp_w:.2f}$$
              $$\\mathbf{{p_w = {f['p_windward']:.2f} \\text{{ kgf/m}}^2}}$$
            """)

    st.markdown(f"""
    ---
    ### **[ส่วนที่ 5]: รายการคำนวณแรงลมด้านตามลม (Leeward) และแรงดันภายในอาคาร (Internal Pressure)**
    ตามมาตรฐาน มยผ. ค่าแรงลมฝั่งตามลมและแรงดันภายในตึกจะคำนวณโดยอ้างอิงหน่วยแรงลมอ้างอิงสูงสุด ณ ระดับหลังคาตึกยอดอาคาร ($H = {H_total:.2f}$ ม.) และใช้ค่านี้เป็นค่าคงที่กระจายเท่ากันตลอดโครงสร้าง:
    
    1. **พิจารณาตัวแปรที่ความสูงยอดตึก ($H = {H_total:.2f}$ ม.):**
       * ค่าสัมประสิทธิ์ความสูง $C_e \\text{{(ยอดอาคาร)}}$ = **`{Ce_H:.3f}`** *(ที่มาสูตร: {Ce_H_exp})*
       * แรงลมอ้างอิงส่วนยอด ($q_h$) = $q \\cdot C_e \\text{{(ยอด)}} = {q:.2f} \\cdot {Ce_H:.3f}$ = **`{qh:.2f}` kgf/m²**
       
    2. **คำนวณแรงลมด้านตามลม (Leeward Pressure: $p_l$):**
       * สมการ: $p_l = I_w \\cdot q_h \\cdot C_g \\cdot C_p \\text{{ (Leeward)}}$
       * แทนค่า: $p_l = {Iw_input:.2f} \\cdot {qh:.2f} \\cdot {Cg_input:.2f} \\cdot ({Cp_l:.2f})$
       * สรุปผลสัมฤทธิ์: $p_l = {Iw_input * qh * Cg_input:.3f} \\cdot ({Cp_l:.2f})$ = **`{p_leeward:.2f}` kgf/m²** *(ค่าเครื่องหมายติดลบหมายถึงมีแรงดูดกระทำดึงผิวหนังออก)*
       
    3. **คำนวณแรงดันสะสมภายในอาคาร (Internal Pressure: $p_{{int}}$):**
       * สมการหลัก: $p_{{int}} = q_h \\cdot (GC_{{pi}})$
       * **กรณีลมดันออกภายใน (Internal Pressure [+]):** $p_{{int+}} = {qh:.2f} \\cdot (+{GCpi:.2f})$ = **`{p_internal_pos:.2f}` kgf/m²**
       * **กรณีลมดูดเข้าภายใน (Internal Suction [-]):** $p_{{int-}} = {qh:.2f} \\cdot (-{GCpi:.2f})$ = **`{p_internal_neg:.2f}` kgf/m²**
    """)

# ------------------------------------------
# TAB 3: Design Output & Export Data
# ------------------------------------------
with tab3:
    st.markdown("#### 💾 สรุปหน่วยแรงลมสุทธิผสมตาม Load Cases สำหรับนำไปกรอกซอฟต์แวร์วิเคราะห์โครงสร้าง")
    st.markdown("วิศวกรโครงสร้างต้องนำแรงลมภายนอกมาคำนวณหักล้างรวมกับแรงดันภายในอาคารตามกฎแรงลมสุทธิ ($p_{{net}} = p_{{ext}} - p_{{int}}$) โดยแบ่งออกเป็น 2 กรณีวิกฤตที่สุด:")

    # สร้างชุดข้อมูลแบบเป็นตารางเพื่อส่งออกแอป
    summary_rows = []
    for f in floors_data:
        p_w = f['p_windward']
        net_w_case1 = p_w - p_internal_neg  # ลมภายนอกพัดอัด + ลมภายในช่วยดูดทางเดียวกัน
        net_w_case2 = p_w - p_internal_pos  # ลมภายนอกพัดอัด + ลมภายในดันสวนทางกัน
        
        summary_rows.append({
            "Story": f"Floor {f['floor_num']}",
            "Elevation Range (m)": f"{f['z_bottom']:.2f} to {f['z_top']:.2f}",
            "Windward Ext. (kgf/m²)": round(p_w, 2),
            "Case 1: Net Windward (p_ext - p_int-)": round(net_w_case1, 2),
            "Case 2: Net Windward (p_ext - p_int+)": round(net_w_case2, 2)
        })
        
    df_summary = pd.DataFrame(summary_rows)
    
    # แสดงผลตารางแบบสะอาดตา
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    # ฟังก์ชันดาวน์โหลดตารางเป็น CSV เพื่อนำไปเปิดใน Microsoft Excel
    csv_data = df_summary.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 ดาวน์โหลดตารางสรุปโหลดนี้เป็นไฟล์สำหรับ Excel (.csv)",
        data=csv_data,
        file_name="Wind_Load_Summary_MJP1311.csv",
        mime="text/csv"
    )
    
    st.markdown(f"""
    <div style="background-color: #EFF6FF; padding: 15px; border-radius: 8px; margin-top: 15px; border-left: 5px solid #1D4ED8;">
    <strong>💡 บันทึกเพิ่มเติมสำหรับผนังด้านตามลม (Leeward Wall Design Summary):</strong><br>
    เนื่องจากแรงลมด้านตามลมมีค่าสม่ำเสมอเท่ากันตลอดทุกช่วงความสูง ค่าแรงลมสุทธิวิกฤตสุดที่กระทำต่อโครงสร้างคือ:<br>
    • <strong>กรณีวิกฤตสุทธิสูงสุด (แรงดูดภายนอก + แรงอัดภายในพัดหนุนกัน):</strong> 
    $p_{{net}} = p_l - p_{{int+}} = {p_leeward:.2f} - ({p_internal_pos:.2f})$ = <strong><span style="color:#DC2626;">{(p_leeward - p_internal_pos):.2f} kgf/m²</span></strong> (เป็นแรงดูดอย่างรุนแรงพยายามดึงผนังให้หลุดออกจากตัวโครงสร้างอาคาร)
    </div>
    """, unsafe_allow_html=True)

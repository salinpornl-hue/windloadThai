import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# ฐานข้อมูลความเร็วลม มยผ. 1311-50
# ==========================================
PROVINCE_V = {
    "กรุงเทพฯ / นนทบุรี / ปทุมธานี / สมุทรปราการ / สมุทรสาคร (25 m/s)": 25.0,
    "ชลบุรี / ระยอง / จันทบุรี / ตราด (30 m/s)": 30.0,
    "ภูเก็ต / พังงา / กระบี่ (27 m/s)": 27.0,
    "เชียงใหม่ / เชียงราย / พิษณุโลก / แม่ฮ่องสอน (25 m/s)": 25.0,
    "นครราชสีมา / ขอนแก่น / อุดรธานี / อุบลราชธานี (25 m/s)": 25.0,
    "สงขลา / สุราษฎร์ธานี / นครศรีธรรมราช (25 m/s)": 25.0,
    "🛠️ กำหนดค่าความเร็วลมเอง (Manual Input)": 25.0
}

# ==========================================
# Core Logic & Math
# ==========================================
def calculate_q(V):
    rho = 1.25  
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665  

def get_Ce_details(z, exposure):
    z_eff = max(z, 6.0) 
    if 'A' in exposure:
        alpha, min_val, max_val = 0.20, 0.9, 1.5
    elif 'B' in exposure:
        alpha, min_val, max_val = 0.28, 0.7, 1.2
    else:
        alpha, min_val, max_val = 0.40, 0.5, 1.0
        
    raw_ce = (z_eff / 10.0) ** alpha
    ce = min(max(raw_ce, min_val), max_val)
    
    explanation = f"สูตรภูมิประเทศ {exposure[:1]}: (z_eff/10)^{alpha} = ({z_eff}/10)^{alpha} = {raw_ce:.4f} → ควบคุมด้วยค่าที่ {ce:.3f}"
    if z < 6.0:
        explanation = f"เนื่องจาก z = {z} ม. ต่ำกว่าขั้นต่ำ (6.0 ม.) ให้ใช้ z = 6.0 ม. | " + explanation
    return ce, explanation

# ==========================================
# Streamlit UI Setup
# ==========================================
st.set_page_config(page_title="Wind Load & Base Shear Analyzer", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.3rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 25px; }
    .section-header { font-size: 1.4rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 15px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    .verdict-box { padding: 15px; border-radius: 8px; font-size: 1.1rem; font-weight: bold; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind Load & Base Shear Analyzer Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบคำนวณแรงลมสุทธิ, พื้นที่รับแรงดันแผ่ (Tributary Area) และเปรียบเทียบแรงเฉือนที่ฐานอาคาร (Base Shear Comparison)</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดและสเปกแรงลม")

st.sidebar.subheader("1. ข้อมูลสถานที่ตั้งและการ Auto-V")
prov_choice = st.sidebar.selectbox("พื้นที่ตั้งอาคาร", list(PROVINCE_V.keys()))

if "Manual Input" in prov_choice:
    V_input = st.sidebar.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
else:
    V_input = PROVINCE_V[prov_choice]
    st.sidebar.info(f"ระบบเลือกใช้ V = {V_input} m/s อัตโนมัติ")

exposure = st.sidebar.selectbox("สภาพภูมิประเทศ (Exposure Class)", ['A (พื้นที่โล่งแจ้ง/ชายฝั่ง)', 'B (พื้นที่ชานเมือง/มีต้นไม้หนาแน่น)', 'C (ในเมืองใหญ่/ตึกสูงหนาแน่น)'])
Iw_input = st.sidebar.selectbox("ค่าประกอบความสำคัญอาคาร (Iw)", [1.0, 1.15], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 2. แรงแผ่นดินไหวเพื่อเปรียบเทียบ")
V_EQ_input = st.sidebar.number_input("แรงเฉือนที่ฐานจากแผ่นดินไหว V_EQ (kN)\n(ได้จากการเปิดเล่มคำนวณแผ่นดินไหว)", value=120.0, step=10.0, min_value=0.0)

st.sidebar.markdown("---")
st.sidebar.subheader("3. สัมประสิทธิ์รูปทรงอาคาร")
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)
Cp_w = st.sidebar.number_input("Cp ผนังรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังตามลม (Leeward)", value=-0.5, step=0.05)
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially)"])
GCpi = 0.55 if "Partially" in enclosure else 0.18

# ==========================================
# MAIN PAGE: Dimensions
# ==========================================
st.markdown('<div class="section-header">🏢 มิติรูปทรงและโครงสร้างระดับความสูงอาคาร</div>', unsafe_allow_html=True)

col_b, col_l, col_n = st.columns(3)
with col_b: B = st.number_input("ความกว้างอาคารแนวขนานลม B (เมตร)", value=15.0, min_value=1.0, step=0.5)
with col_l: L = st.number_input("ความยาวอาคารแนวตั้งฉากลม L (เมตร)", value=20.0, min_value=1.0, step=0.5)
with col_n: num_stories = st.number_input("จำนวนชั้นของอาคารทั้งหมด", value=3, min_value=1, step=1)

with st.expander("📐 ปรับแต่งความสูงแยกแต่ละชั้น", expanded=True):
    floor_cols = st.columns(min(num_stories, 4))
    floor_heights = []
    for i in range(num_stories):
        col_idx = i % 4
        default_h = 4.0 if i == 0 else 3.5 
        with floor_cols[col_idx]:
            h_val = st.number_input(f"ความสูงชั้นที่ {i+1} (ม.)", value=default_h, min_value=1.0, step=0.1, key=f"h_f_{i}")
            floor_heights.append(h_val)

H_total = sum(floor_heights)

# ==========================================
# Engine Core Processing
# ==========================================
q = calculate_q(V_input)
Ce_H, _ = get_Ce_details(H_total, exposure)
qh = q * Ce_H

p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_internal_pos = qh * GCpi     
p_internal_neg = qh * (-GCpi)  

net_l_case1 = p_leeward - p_internal_neg  
net_l_case2 = p_leeward - p_internal_pos  

z_cumulative = 0
floors_data = []

for i in range(num_stories):
    h_current = floor_heights[i]
    z_bottom = z_cumulative
    z_top = z_cumulative + h_current
    z_mid = (z_bottom + z_top) / 2.0 
    
    Ce_mid, Ce_mid_exp = get_Ce_details(z_mid, exposure)
    p_w_z = Iw_input * q * Ce_mid * Cg_input * Cp_w
    
    net_w_case1 = p_w_z - p_internal_neg
    net_w_case2 = p_w_z - p_internal_pos
    
    # คำนวณพื้นที่รับลมของชั้นนี้ (Tributary Area) = ความยาวอาคาร L * ความสูงชั้น h
    trib_area = L * h_current
    
    # Story Force (kN) = (p_net_windward + |p_net_leeward|) * Area / 100 
    # (หมายเหตุ: แรงลมรวมคิดจากแรงผลักด้านหน้า + แรงดูดดึงด้านหลังอาคารรวมกัน)
    f_story_kgf_c1 = (net_w_case1 + abs(net_l_case1)) * trib_area
    f_story_kn_c1 = f_story_kgf_c1 * 0.00980665
    
    f_story_kgf_c2 = (net_w_case2 + abs(net_l_case2)) * trib_area
    f_story_kn_c2 = f_story_kgf_c2 * 0.00980665
    
    floors_data.append({
        "floor_num": i + 1, "height": h_current, "z_bottom": z_bottom, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "p_windward": p_w_z, "trib_area": trib_area,
        "net_w_case1": net_w_case1, "net_w_case2": net_w_case2,
        "f_story_kn_c1": f_story_kn_c1, "f_story_kn_c2": f_story_kn_c2
    })
    z_cumulative = z_top

# หาแรงเฉือนที่ฐานรวมจากลม (Base Shear from Wind)
V_wind_case1 = sum([f['f_story_kn_c1'] for f in floors_data])
V_wind_case2 = sum([f['f_story_kn_c2'] for f in floors_data])
V_wind_max = max(V_wind_case1, V_wind_case2)

# ==========================================
# Function วาดรูปหน้าตัดแรงลม (Cross Section)
# ==========================================
def plot_cross_section(floors, view_mode):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], fill="toself", fillcolor="rgba(30, 58, 138, 0.05)", line=dict(color="#1E3A8A", width=3)))
    
    for f in floors:
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="rgba(75, 85, 99, 0.3)", width=1.5, dash="dash"))
        val_w = f['p_windward'] if view_mode == "External" else (f['net_w_case1'] if view_mode == "Case 1" else f['net_w_case2'])
        arrow_len = 1.5 + abs(val_w) / 30.0
        fig.add_annotation(x=0, y=f['z_mid'], ax=-arrow_len, ay=f['z_mid'], xref="x", yref="y", axref="x", ayref="y",
                           text=f"<b>{val_w:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowcolor="#DC2626")
    
    val_l = p_leeward if view_mode == "External" else (net_l_case1 if view_mode == "Case 1" else net_l_case2)
    fig.add_annotation(x=B, y=H_total/2, ax=B+2, ay=H_total/2, text=f"<b>{val_l:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowcolor="#EA580C")
    
    fig.update_layout(title="<b>1. แผนภาพหน่วยแรงลมหน้าตัดอาคาร (Cross Section View)</b>", xaxis_title="ความกว้างอาคาร B (ม.)", yaxis_title="ความสูง z (ม.)", xaxis_range=[-5, B+5], yaxis_range=[-1, H_total+2], height=400, plot_bgcolor="white")
    return fig

# ==========================================
# Function วาดรูปพื้นที่รับแรงลม (Front Elevation)
# ==========================================
def plot_front_elevation(floors, L):
    fig = go.Figure()
    # วาดแผงผนังรับลมทั้งหมดแยกสีตามชั้น เพื่อให้เห็นว่าหน่วย kgf/m2 คูณกับพื้นที่ตรงไหนถึงตรงไหน
    for f in floors:
        fig.add_trace(go.Scatter(
            x=[0, L, L, 0, 0], 
            y=[f['z_bottom'], f['z_bottom'], f['z_top'], f['z_top'], f['z_bottom']],
            fill="toself", 
            name=f"ชั้น {f['floor_num']}",
            text=f"<b>ชั้น {f['floor_num']}</b><br>ขอบเขตระดับสูง: {f['z_bottom']:.1f} ถึง {f['z_top']:.1f} ม.<br>ความยาวผนัง L: {L} ม.<br>พื้นที่รับลม: {f['trib_area']:.1f} m²",
            hoverinfo="text"
        ))
        # ใส่ป้ายข้อความแสดงพื้นที่ตรงกลางแผงชั้น
        fig.add_annotation(x=L/2, y=f['z_mid'], text=f"<b>Area = {f['trib_area']:.1f} m²</b><br>(กว้าง {L}ม. × สูง {f['height']}ม.)", showarrow=False, font=dict(color="white", size=11))

    fig.update_layout(title="<b>2. แผนภาพขอบเขตพื้นที่รับลมหน้าตรง (Front Elevation - Tributary Area)</b>", xaxis_title="ความยาวอาคารตั้งฉากลม L (ม.)", yaxis_title="ระดับความสูง z (ม.)", height=400, plot_bgcolor="white")
    return fig

# ==========================================
# TABS NAVIGATION
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 แดชบอร์ด & การกระจายพื้นที่แรงลม", "⚖️ ตรวจสอบ Base Shear (Wind vs EQ)", "📑 รายการคำนวณ"])

# ------------------------------------------
# TAB 1: Area & Pressure Distribution
# ------------------------------------------
with tab1:
    st.markdown("#### 📐 การกระจายแรงดันแผ่ ($kgf/m^2$) ลงบนพื้นที่โครงสร้าง ($m^2$)")
    st.info("💡 **อธิบายทางวิศวกรรม:** หน่วย `kgf/m²` คือ แรงดันลมที่กดลงบนฝาบ้านทุกๆ 1 ตารางเมตร โปรแกรมจะแปลงเป็นแรงลัพธ์แบบจุด (`kN`) ของชั้นนั้นๆ โดยการนำไปคูณกับ **'พื้นที่รับลมหน้าตรง (Tributary Area)'** ซึ่งมีขอบเขตตั้งแต่ระดับกึ่งกลางชั้นล่างถึงกึ่งกลางชั้นบน ยาวตลอดแนวอาคารด้านรับลม ดังแสดงในรูปภาพด้านขวา")
    
    view_option = st.radio("เลือกกรณีโหลดเพื่อดูแผนภาพแรงดัน:", ["External", "Case 1", "Case 2"], horizontal=True)
    
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.plotly_chart(plot_cross_section(floors_data, view_option), use_container_width=True)
    with g_col2:
        st.plotly_chart(plot_front_elevation(floors_data, L), use_container_width=True)

# ------------------------------------------
# TAB 2: Base Shear Comparison
# ------------------------------------------
with tab2:
    st.markdown("#### ⚖️ การเปรียบเทียบแรงเฉือนที่ฐานอาคารรวม (Total Base Shear Comparison)")
    
    # ตรวจสอบว่าแรงไหนชนะ
    governing_force = "WIND LOAD (แรงลม)" if V_wind_max > V_EQ_input else "EARTHQUAKE LOAD (แรงแผ่นดินไหว)"
    color_box = "#FEE2E2" if V_wind_max > V_EQ_input else "#E0F2FE"
    border_color = "#EF4444" if V_wind_max > V_EQ_input else "#0284C7"
    
    # วาดกราฟแท่งเปรียบเทียบ
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=["Wind Load (Case 1)", "Wind Load (Case 2)", "Earthquake (V_EQ)"],
        y=[V_wind_case1, V_wind_case2, V_EQ_input],
        marker_color=["#3B82F6", "#1D4ED8", "#EF4444"],
        text=[f"{V_wind_case1:.2f} kN", f"{V_wind_case2:.2f} kN", f"{V_EQ_input:.2f} kN"],
        textposition='auto'
    ))
    fig_bar.update_layout(title="<b>กราฟเปรียบเทียบแรงรวมที่ฐานอาคาร (Base Shear) หน่วย: kN</b>", yaxis_title="Base Shear (kN)", height=350, plot_bgcolor="white")
    
    b_col1, b_col2 = st.columns([3, 2])
    with b_col1:
        st.plotly_chart(fig_bar, use_container_width=True)
    with b_col2:
        st.markdown(f"""
        <div class="verdict-box" style="background-color: {color_box}; border-left: 6px solid {border_color};">
            📋 ผลลัพธ์การตรวจสอบระบบแรงด้านข้าง:<br>
            <span style="font-size: 1.3rem; color: {border_color};">{governing_force} เป็นตัวควบคุมหลัก!</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        **💡 บันทึกข้อเสนอแนะสำหรับการออกแบบโครงสร้าง:**
        * **แรงลัพธ์รวมจากลมสูงสุด ($V_{{Wind}}$):** `{V_wind_max:.2f}` kN
        * **แรงลัพธ์จากแผ่นดินไหว ($V_{{EQ}}$):** `{V_EQ_input:.2f}` kN
        * อัตราส่วนระบบแรง $V_{{Wind}} / V_{{EQ}}$ = **`{V_wind_max / (V_EQ_input if V_EQ_input > 0 else 1):.2f}`** เท่า
        """)
        if V_wind_max > V_EQ_input:
            st.success("🎯 **คำแนะนำ:** สำหรับอาคารนี้ โครงสร้างรับแรงด้านข้าง (เช่น เสา, คาน, ระบบค้ำยัน) ควรออกแบบโดยอ้างอิงแรงลมเป็นหลัก เนื่องจากมีค่ามากกว่าแรงแผ่นดินไหว")
        else:
            st.warning("🎯 **คำแนะนำ:** แรงแผ่นดินไหวมีค่าสูงกว่า! โครงสร้างหลัก (รวมถึงเสาตอม่อและระบบฐานราก) จะต้องได้รับการตรวจสอบรายละเอียดความเหนียวและการดัดงอตามมาตรฐานการต้านทานแผ่นดินไหว")

# ------------------------------------------
# TAB 3: Report & Outputs
# ------------------------------------------
with tab3:
    st.markdown("#### 📑 ตารางสรุปหน่วยแรง, พื้นที่ และแรงลัพธ์รายชั้นประจำจุดโครงสร้าง")
    
    summary_rows = []
    for f in floors_data:
        summary_rows.append({
            "Story": f"Floor {f['floor_num']}",
            "ขอบเขตพื้นที่ความสูง (ม.)": f"{f['z_bottom']:.1f} ถึง {f['z_top']:.1f}",
            "พื้นที่รับลม Trib Area (m²)": round(f['trib_area'], 1),
            "Net Windward C1 (kgf/m²)": round(f['net_w_case1'], 1),
            "Net Leeward C1 (kgf/m²)": round(net_l_case1, 1),
            "🔥 Story Force C1 (kN)": round(f['f_story_kn_c1'], 2),
            "Net Windward C2 (kgf/m²)": round(f['net_w_case2'], 1),
            "Net Leeward C2 (kgf/m²)": round(net_l_case2, 1),
            "🔥 Story Force C2 (kN)": round(f['f_story_kn_c2'], 2)
        })
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    st.markdown(f"""
    ---
    ### **📊 สมการถอดตัวเลขให้เห็นที่มาของหน่วย:**
    ยกตัวอย่าง **ชั้นที่ 1:**
    * หน่วยแรงดันกระทำแผ่ฝั่งรับลม ($p_{{net, w}}$) = `{floors_data[0]['net_w_case1']:.2f}` $kgf/m^2$
    * หน่วยแรงดันกระทำแผ่ฝั่งตามลม ($p_{{net, l}}$) = `{net_l_case1:.2f}` $kgf/m^2$ *(แรงดูด)*
    * พื้นที่รับลมแผ่หน้าตรงของชั้นนี้ ($A_{{trib}}$) = ความยาวอาคาร $L$ (`{L}` ม.) $\\times$ ความสูงชั้น (`{floors_data[0]['height']}` ม.) = **`{floors_data[0]['trib_area']:.1f}` $m^2$**
    * **สมการแปลงค่า:** $F_{{story}} = (p_{{net, w}} + |p_{{net, l}}|) \\times A_{{trib}} \\times 0.00980665$
    * แทนค่า: $F_{{story}} = ({floors_data[0]['net_w_case1']:.2f} + {abs(net_l_case1):.2f}) \\times {floors_data[0]['trib_area']:.1f} \\times 0.00980665$ = **`{floors_data[0]['f_story_kn_c1']:.2f}` kN**
    """)

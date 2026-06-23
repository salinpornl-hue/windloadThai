import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# Core Logic & Math (มยผ. 1311-50 / มยผ. 1302)
# ==========================================
def calculate_q(V):
    """คำนวณหน่วยแรงลมอ้างอิง q (kgf/m²)"""
    rho = 1.25  
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665  

def get_Ce_details(z, exposure):
    """คำนวณ Ce อิงตามประเภทภูมิประเทศพร้อมส่งคำอธิบายสูตร"""
    z_eff = max(z, 6.0) 
    if 'A' in exposure:
        alpha, min_val, max_val = 0.20, 0.9, 1.5
    elif 'B' in exposure:
        alpha, min_val, max_val = 0.28, 0.7, 1.2
    else:
        alpha, min_val, max_val = 0.40, 0.5, 1.0
        
    raw_ce = (z_eff / 10.0) ** alpha
    ce = min(max(raw_ce, min_val), max_val)
    
    explanation = f"สูตรภูมิประเทศ {exposure[:1]}: (z_eff/10)^{alpha} = ({z_eff}/10)^{alpha} = {raw_ce:.4f} → ใช้ค่าควบคุม {ce:.3f}"
    if z < 6.0:
        explanation = f"เนื่องจากระดับพิจารณา z = {z} ม. ต่ำกว่าขั้นต่ำ (6.0 ม.) จึงปรับใช้ z_eff = 6.0 ม. | " + explanation
    return ce, explanation

# ==========================================
# Streamlit UI Setup & Styling
# ==========================================
st.set_page_config(page_title="Wind & Seismic Load Analyzer Pro", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.3rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 25px; }
    .section-header { font-size: 1.4rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 15px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    .verdict-box { padding: 15px; border-radius: 8px; font-size: 1.1rem; font-weight: bold; margin-top: 10px; }
    .math-info { background-color: #F8FAFC; padding: 12px; border-left: 4px solid #3B82F6; border-radius: 4px; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind & Seismic Load Analyzer (มยผ. 1311-50 / 1302)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบวิเคราะห์แรงลมสุทธิ, ขอบเขตพื้นที่รับแรงดันแผ่ (Tributary Area) และตรวจสอบแรงเฉือนฐานอาคารเปรียบเทียบภัยพิบัติ</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดและสเปกแรงด้านข้าง")

st.sidebar.subheader("1. ข้อกำหนดแรงลม (มยผ. 1311-50)")
V_input = st.sidebar.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
exposure = st.sidebar.selectbox("สภาพภูมิประเทศ (Exposure Class)", ['A (พื้นที่โล่งแจ้ง/ชายฝั่ง)', 'B (พื้นที่ชานเมือง/มีต้นไม้หนาแน่น)', 'C (ในเมืองใหญ่/ตึกสูงหนาแน่น)'])
Iw_input = st.sidebar.selectbox("ค่าประกอบความสำคัญอาคารแรงลม (Iw)", [1.0, 1.15], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 2. ข้อกำหนดแรงแผ่นดินไหว (มยผ. 1302)")
eq_mode = st.sidebar.radio("วิธีการคำนวณแรงแผ่นดินไหว (V_EQ):", ["ให้โปรแกรมประมาณการสถิตเทียบเท่า", "ระบุค่าแรงเฉือนฐานเองโดยตรง (Direct kN)"])

if eq_mode == "ให้โปรแกรมประมาณการสถิตเทียบเท่า":
    w_dl_ll = st.sidebar.number_input("น้ำหนักตึกรวมเฉลี่ยรายชั้น (kgf/m²)\n(รวม Dead Load + %Live Load)", value=600.0, step=50.0)
    cs_coeff = st.sidebar.number_input("สัมประสิทธิ์แรงแผ่นดินไหว Cs", value=0.050, step=0.005, format="%.3f")
else:
    V_EQ_manual = st.sidebar.number_input("ระบุค่าแรงเฉือนฐานแผ่นดินไหว V_EQ (kN)", value=120.0, step=10.0, min_value=0.0)

st.sidebar.markdown("---")
st.sidebar.subheader("3. สัมประสิทธิ์รูปทรงอาคาร (Cp, Cg)")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อมของอาคาร", ["อาคารปิดทึบ (Enclosed Building)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)
Cp_w = st.sidebar.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)
Cp_s = st.sidebar.number_input("Cp ผนังด้านข้าง (Sidewall)", value=-0.7, step=0.05)
Cp_r = st.sidebar.number_input("Cp หลังคาแบน (Flat Roof Uplift)", value=-0.7, step=0.05)

GCpi = 0.55 if "Partially" in enclosure else 0.18

# ==========================================
# MAIN PAGE: Dimensions Input
# ==========================================
st.markdown('<div class="section-header">🏢 มิติรูปทรงและโครงสร้างระดับความสูงอาคาร</div>', unsafe_allow_html=True)

col_b, col_l, col_n = st.columns(3)
with col_b: B = st.number_input("ความกว้างอาคารขนานลม B (เมตร)", value=15.0, min_value=1.0, step=0.5)
with col_l: L = st.number_input("ความยาวอาคารตั้งฉากลม L (เมตร)", value=20.0, min_value=1.0, step=0.5)
with col_n: num_stories = st.number_input("จำนวนชั้นของอาคารทั้งหมด", value=3, min_value=1, step=1)

with st.expander("📐 คลิกเพื่อปรับแต่งความสูงแยกแต่ละชั้น", expanded=True):
    floor_cols = st.columns(min(num_stories, 4))
    floor_heights = []
    for i in range(num_stories):
        col_idx = i % 4
        default_h = 4.0 if i == 0 else 3.5 
        with floor_cols[col_idx]:
            h_val = st.number_input(f"ความสูงชั้นที่ {i+1} (ม.)", value=default_h, min_value=1.0, step=0.1, key=f"h_f_{i}")
            floor_heights.append(h_val)

H_total = sum(floor_heights)

# --- คำนวณที่มาแรงแผ่นดินไหว ---
if eq_mode == "ให้โปรแกรมประมาณการสถิตเทียบเท่า":
    W_building_kgf = (B * L) * num_stories * w_dl_ll
    W_building_kN = W_building_kgf * 0.00980665
    V_EQ_calculated = cs_coeff * W_building_kN
    eq_source_details = f"ประมาณการตาม มยผ. 1302: น้ำหนักโครงสร้างอาคารรวม $W = B \\times L \\times \\text{{ชั้น}} \\times \\text{{น้ำหนักเฉลี่ย}} = {W_building_kN:.2f}$ kN, ใช้สัมประสิทธิ์แรงแผ่นดินไหว $C_s = {cs_coeff:.3f} \\rightarrow V_{{EQ}} = C_s \\times W = {V_EQ_calculated:.2f}$ kN"
else:
    V_EQ_calculated = V_EQ_manual
    eq_source_details = f"ระบุค่าควบคุมโดยตรงจากผลวิเคราะห์ภายนอกอาคาร: $V_{{EQ}} = {V_EQ_calculated:.2f}$ kN"

# ตรวจสอบความเพรียวอาคาร
slenderness = H_total / B
if H_total > 40.0 or slenderness > 4.0:
    st.warning(f"⚠️ **ข้อพิจารณาทางวิศวกรรม:** อาคารสูง {H_total:.2f} ม. หรือความเพรียว H/B = {slenderness:.2f} เข้าข่ายเป็นอาคารไหวตัวง่าย ควรพิจารณาคำนวณค่า Cg ด้วยวิธีกระแสน้ำวนพลศาสตร์เพิ่มเติม")

# ==========================================
# Engine Core Processing
# ==========================================
q = calculate_q(V_input)
Ce_H, Ce_H_exp = get_Ce_details(H_total, exposure)
qh = q * Ce_H

# โหลดคงที่ที่ระดับหลังคาและแรงดันภายใน
p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_sidewall_ext = Iw_input * qh * Cg_input * Cp_s
p_roof_ext = Iw_input * qh * Cg_input * Cp_r

p_internal_pos = qh * GCpi     
p_internal_neg = qh * (-GCpi)  

# Net Pressure ของส่วนที่คงที่
net_l_case1 = p_leeward - p_internal_neg
net_l_case2 = p_leeward - p_internal_pos
net_s_case1 = p_sidewall_ext - p_internal_neg
net_s_case2 = p_sidewall_ext - p_internal_pos
net_r_case1 = p_roof_ext - p_internal_neg
net_r_case2 = p_roof_ext - p_internal_pos

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
    
    # 🎯 [Tributary Area] คำนวณขอบเขตพื้นที่รับแรงแผ่รายชั้นอย่างละเอียด
    trib_area_front = L * h_current  # ผนังด้านตั้งฉากลม (ใช้คำนวณแรงหลักประจำชั้น)
    trib_area_side = B * h_current   # ผนังด้านขนานลม
    
    # คำนวณ Story Force (kN) = (Net Windward - Net Leeward) * Trib_Area * conversion
    # เนื่องจาก Leeward เป็นลบ (ทิศทางดึงออกขวาเหมือนกัน) การลบกันทางพีชคณิตจึงเป็นการบวกขนาดแรง
    f_story_kn_c1 = (net_w_case1 - net_l_case1) * trib_area_front * 0.00980665
    f_story_kn_c2 = (net_w_case2 - net_l_case2) * trib_area_front * 0.00980665
    
    floors_data.append({
        "floor_num": i + 1, "height": h_current, "z_bottom": z_bottom, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "Ce_exp": Ce_mid_exp, "p_windward": p_w_z,
        "net_w_case1": net_w_case1, "net_w_case2": net_w_case2,
        "trib_area_front": trib_area_front, "trib_area_side": trib_area_side,
        "f_story_kn_c1": f_story_kn_c1, "f_story_kn_c2": f_story_kn_c2
    })
    z_cumulative = z_top

V_wind_case1 = sum([f['f_story_kn_c1'] for f in floors_data])
V_wind_case2 = sum([f['f_story_kn_c2'] for f in floors_data])
V_wind_max = max(V_wind_case1, V_wind_case2)

# ==========================================
# Helper Function: วาดรูปสัดส่วนพื้นที่หน้าตรง/ด้านตัด
# ==========================================
def plot_cross_section_full(floors, view_mode):
    fig = go.Figure()
    # วาดตัวตึก
    fig.add_trace(go.Scatter(x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], fill="toself", fillcolor="rgba(30, 58, 138, 0.03)", line=dict(color="#1E3A8A", width=3), name="โครงสร้าง"))
    
    # พล็อตลูกศรแรงลมรับลมรายชั้น
    for f in floors:
        val_w = f['p_windward'] if view_mode == "External" else (f['net_w_case1'] if view_mode == "Case 1" else f['net_w_case2'])
        arrow_len = 1.5 + abs(val_w) / 40.0
        fig.add_annotation(x=0, y=f['z_mid'], ax=-arrow_len, ay=f['z_mid'], xref="x", yref="y", axref="x", ayref="y", text=f"<b>{val_w:.1f}</b>", showarrow=True, arrowhead=2, arrowcolor="#DC2626")
        
    # พล็อตแรงดันตามลม (Leeward)
    val_l = p_leeward if view_mode == "External" else (net_l_case1 if view_mode == "Case 1" else net_l_case2)
    fig.add_annotation(x=B, y=H_total/2, ax=B+(1.5 + abs(val_l)/40.0), ay=H_total/2, text=f"<b>Leeward: {val_l:.1f}</b>", showarrow=True, arrowhead=2, arrowcolor="#EA580C")
    
    # พล็อตแรงยกหลังคา (Roof Uplift)
    val_r = p_roof_ext if view_mode == "External" else (net_r_case1 if view_mode == "Case 1" else net_r_case2)
    fig.add_annotation(x=B/2, y=H_total+(1.5 + abs(val_r)/40.0), ax=B/2, ay=H_total, text=f"<b>Roof Uplift: {val_r:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowcolor="#9333EA")
    
    fig.update_layout(title="<b>1. แผนภาพหน่วยแรงดันลมบนหน้าตัดอาคาร (Cross Section View: kgf/m²)</b>", xaxis_title="ความกว้างตึก B (ม.)", yaxis_title="ความสูงอาคาร z (ม.)", xaxis_range=[-6, B+6], yaxis_range=[-1, H_total+4], height=450, plot_bgcolor="white")
    return fig

def plot_tributary_area(floors, length_dim, side_label="Front (L)"):
    fig = go.Figure()
    for f in floors:
        area_val = f['trib_area_front'] if "Front" in side_label else f['trib_area_side']
        fig.add_trace(go.Scatter(
            x=[0, length_dim, length_dim, 0, 0], y=[f['z_bottom'], f['z_bottom'], f['z_top'], f['z_top'], f['z_bottom']],
            fill="toself", name=f"ชั้น {f['floor_num']}",
            text=f"<b>ชั้น {f['floor_num']}</b><br>ระดับขอบเขต: {f['z_bottom']:.1f} ม. ถึง {f['z_top']:.1f} ม.<br>พื้นที่รับแรง: {area_val:.1f} m²", hoverinfo="text"
        ))
        # แสดงข้อความบอกมิติสี่เหลี่ยมในเนื้อที่ให้เห็นชัดเจน
        fig.add_annotation(x=length_dim/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor_num']}: Area = {area_val:.1f} m²</b><br>(กว้าง {length_dim}ม. × สูงช่วงชั้น {f['height']}ม.)", showarrow=False, font=dict(color="white", size=11))
        
    fig.update_layout(title=f"<b>2. ขอบเขตพื้นที่รับลมหน้าตรง (Elevation View - ด้าน {side_label})</b>", xaxis_title="ความยาวหน้าแผงผนังรับแรง (ม.)", yaxis_title="ระดับความสูงของอาคาร z (ม.)", height=450, plot_bgcolor="white", showlegend=False)
    return fig

# ==========================================
# TABS SYSTEM
# ==========================================
tab1, tab2, tab3 = st.tabs(["🖼️ ขอบเขตพื้นที่รับลม (Tributary Area)", "⚖️ ตรวจสอบเปรียบเทียบ Base Shear", "📑 รายการคำนวณ & ตารางส่งออก"])

# ------------------------------------------
# TAB 1: Tributary Area Visualizer
# ------------------------------------------
with tab1:
    st.markdown("#### 📐 แผนภาพแสดงพิกัดการถ่ายแรงดันกระจายแผ่ ($kgf/m^2$) ลงบนพื้นที่โครงสร้างจริง ($m^2$)")
    st.info("💡 **หลักการวิศวกรรมโครงสร้าง:** หน่วยแรงดันแบบกระจาย ($kgf/m^2$) จะไม่สามารถรวมเป็นแรงเฉือนฐานอาคารได้โดยตรงจนกว่าจะถูกนำไปคูณกับ **'พื้นที่รับลมแยกรายชั้น (Tributary Area)'** ซึ่งจะแบ่งขอบเขตกึ่งกลางชั้นล่างถึงกึ่งกลางชั้นบนและแผ่เต็มความยาวฝาผนังอาคาร โปรแกรมทำการถอดเนื้อที่สี่เหลี่ยมผืนผ้าออกมาให้เห็นขอบเขตตามรูปด้านขวาเพื่อนำไปคำนวณเป็นแรงลัพธ์จุดรวมประจำชั้น (`kN`) ต่อไป")
    
    view_option = st.radio("เลือกกรณีโหลดแรงลมเพื่อพล็อตแผนภาพทิศทางแรงดัน:", ["External", "Case 1", "Case 2"], horizontal=True)
    
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.plotly_chart(plot_cross_section_full(floors_data, view_option), use_container_width=True)
    with g_col2:
        st.plotly_chart(plot_tributary_area(floors_data, L, "Front View (L)"), use_container_width=True)
        
    st.markdown("---")
    st.markdown("##### 🧱 เพิ่มเติม: ขอบเขตพื้นที่รับลมด้านข้าง (Side View สำหรับคำนวณโครงเคร่วกระจก/Cladding และแรงลมในทิศทางรอง)")
    st.plotly_chart(plot_tributary_area(floors_data, B, "Side View (B)"), use_container_width=True)

# ------------------------------------------
# TAB 2: Base Shear Analyzer
# ------------------------------------------
with tab2:
    st.markdown("#### ⚖️ ระบบตรวจสอบเปรียบเทียบแรงเฉือนที่ฐานอาคารทันที (Total Base Shear Comparison)")
    st.markdown(f"**ℹ️ เอกสารอ้างอิงและที่มาของแรงแผ่นดินไหว ($V_{{EQ}}$):** {eq_source_details}")
    
    governing_force = "WIND LOAD (แรงลมสุทธิควบคุมการออกแบบ)" if V_wind_max > V_EQ_calculated else "EARTHQUAKE LOAD (แรงแผ่นดินไหวควบคุมการออกแบบ)"
    color_box = "#FEE2E2" if V_wind_max > V_EQ_calculated else "#E0F2FE"
    border_color = "#EF4444" if V_wind_max > V_EQ_calculated else "#0284C7"
    
    # พล็อตบาร์เปรียบเทียบ
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=["แรงลม Case 1 (-Internal Suction)", "แรงลม Case 2 (+Internal Pressure)", "แรงแผ่นดินไหวควบคุม (V_EQ)"],
        y=[V_wind_case1, V_wind_case2, V_EQ_calculated],
        marker_color=["#3B82F6", "#1D4ED8", "#EF4444"],
        text=[f"{V_wind_case1:.2f} kN", f"{V_wind_case2:.2f} kN", f"{V_EQ_calculated:.2f} kN"],
        textposition='auto'
    ))
    fig_bar.update_layout(title="<b>เปรียบเทียบแรงเฉือนรวมที่ฐานราก (Total Base Shear Comparison) หน่วย: kN</b>", yaxis_title="Base Shear (kN)", height=380, plot_bgcolor="white")
    
    b_col1, b_col2 = st.columns([3, 2])
    with b_col1:
        st.plotly_chart(fig_bar, use_container_width=True)
    with b_col2:
        st.markdown(f"""
        <div class="verdict-box" style="background-color: {color_box}; border-left: 6px solid {border_color}; margin-bottom: 20px;">
            📋 ผลวิเคราะห์และข้อตัดสินแรงด้านข้างควบคุม:<br>
            <span style="font-size: 1.25rem; color: {border_color};">{governing_force}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        **📊 สรุปตัวเลขเชิงเปรียบเทียบมติโครงสร้าง:**
        * **แรงเฉือนรวมที่ฐานอาคารจากลมสูงสุด ($V_{{Wind, max}}$):** `{V_wind_max:.2f}` kN
        * **แรงเฉือนรวมที่ฐานอาคารจากแผ่นดินไหว ($V_{{EQ}}$):** `{V_EQ_calculated:.2f}` kN
        * อัตราส่วนสัดส่วนแรงทำลายล้างจากภัยพิบัติ $V_{{Wind}} / V_{{EQ}}$ = **`{V_wind_max / (V_EQ_calculated if V_EQ_calculated > 0 else 1):.2f}`** เท่า
        """)
        
        if V_wind_max > V_EQ_calculated:
            st.success("🎯 **คำแนะนำในการจัดส่งแบบ:** อาคารชุดนี้ถูกควบคุมโครงสร้างด้วยแรงลมเป็นหลัก ให้ใช้ค่าแรงลมรายชั้นป้อนในโมเดลโครงสร้างเพื่อเช็กเสา-คาน แต่อย่าลืมเสริมเหล็กปลอกขั้นต่ำต้านแผ่นดินไหวตามเทศบัญญัติกฎหมาย")
        else:
            st.warning("🎯 **คำแนะนำในการจัดส่งแบบ:** แรงแผ่นดินไหวมีค่าวิกฤตกว่าแรงลม! โครงสร้างต้องได้รับการออกแบบและจัดรายละเอียดเหล็กเสริมให้มีความเหนียว (Ductile Detailing) ตามมาตรฐาน มยผ. 1301/1302 เพื่อป้องกันการพังทลายแบบฉับพลัน")

# ------------------------------------------
# TAB 3: Calculation Book & Export Table
# ------------------------------------------
with tab3:
    st.markdown("#### 💾 ตารางสรุปหน่วยแรงและแรงลัพธ์รายชั้นแบบบูรณาการ (สำหรับป้อนโปรแกรมวิเคราะห์โครงสร้าง)")
    
    summary_rows = []
    for f in floors_data:
        summary_rows.append({
            "Story": f"Floor {f['floor_num']}",
            "ความสูงช่วงชั้น (ม.)": f"{f['z_bottom']:.1f} ถึง {f['z_top']:.1f}",
            "พื้นที่รับลมหน้าตรง A_front (m²)": round(f['trib_area_front'], 1),
            "Net Windward C1 (kgf/m²)": round(f['net_w_case1'], 1),
            "Net Leeward C1 (kgf/m²)": round(net_l_case1, 1),
            "🔥 Story Force C1 (kN)": round(f['f_story_kn_c1'], 2),
            "Net Windward C2 (kgf/m²)": round(f['net_w_case2'], 1),
            "Net Leeward C2 (kgf/m²)": round(net_l_case2, 1),
            "🔥 Story Force C2 (kN)": round(f['f_story_kn_c2'], 2)
        })
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    csv_data = df_summary.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="📥 ดาวน์โหลดตารางสรุปข้อมูลแบบบูรณาการ (.csv)", data=csv_data, file_name="Wind_And_Seismic_Design_Report.csv", mime="text/csv")
    
    st.markdown("---")
    st.markdown("#### 📑 เล่มเอกสารรายการคำนวณถอดสูตรโดยละเอียดประจำโครงการ")
    
    st.markdown(f"""
    **1. ตัวแปรอ้างอิงและแรงดันลมอ้างอิงตั้งต้น ($q$)**
    * ความเร็วลมออกแบบพิจารณา $V = {V_input}$ m/s $\\rightarrow q = 0.5 \\times 1.25 \\times V^2 / 9.80665 =$ **`{q:.2f}` kgf/m²**
    * ค่าประกอบความสำคัญ $I_w = {Iw_input}$, ตัวประกอบลมกระโชก $C_g = {Cg_input}$
    * แรงดันลมที่ยอดอาคารที่ระดับสูง $H$ (`{H_total:.2f}` ม.): ค่า $C_{{e,H}} = {Ce_H:.3f}$ $\\rightarrow q_h = q \\times C_{{e,H}} =$ **`{qh:.2f}` kgf/m²**
    
    **2. หน่วยแรงลมภายนอกส่วนคงที่และหน่วยแรงดันผนังด้านข้าง (Sidewalls / Roof)**
    * ผนังตามลม (Leeward Exterior): $p_l = I_w \\times q_h \\times C_g \\times C_p = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_l}) =$ **`{p_leeward:.2f}` kgf/m²**
    * ผนังด้านข้างอาคาร (Sidewall Exterior): $p_s = I_w \\times q_h \\times C_g \\times C_p = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_s}) =$ **`{p_sidewall_ext:.2f}` kgf/m²**
    * แรงยกหลังคาแบน (Roof Uplift Exterior): $p_{{roof}} = I_w \\times q_h \\times C_g \\times C_p = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_r}) =$ **`{p_roof_ext:.2f}` kgf/m²**
    """)
    
    st.markdown("##### 🧮 การถอดสเต็ปแปลงหน่วย $kgf/m^2 \\rightarrow kN$ แยกตามรายชั้นอาคาร:")
    for f in floors_data:
        with st.expander(f"🔍 ดูสเต็ปคำนวณและที่มาของ: ชั้นที่ {f['floor_num']} (ระดับพิจารณากึ่งกลางชั้น {f['z_mid']:.2f} ม.)", expanded=False):
            st.markdown(f"""
            * **สัมประสิทธิ์ปรับความสูงชั้น:** $C_e = {f['Ce']:.3f}$ *(คำนวณจาก {f['Ce_exp']})*
            * **แรงดันภายนอกด้านรับลม:** $p_w = {Iw_input} \\times {q:.2f} \\times {f['Ce']:.3f} \\times {Cg_input} \\times {Cp_w} = {f['p_windward']:.2f}$ kgf/m²
            * **ขอบเขตพื้นที่รับลมหน้าตรง ($A_{{trib}}$):** ความยาวตึก $L = {L}$ ม. $\\times$ ความสูงเฉพาะชั้น $h = {f['height']}$ ม. = **`{f['trib_area_front']:.1f}` m²**
            
            **📌 ถอดสมการแปลงค่าแรงลัพธ์ประจำชั้น Case 1 (+ แรงดูดภายในอาคาร $p_{{int-}} = {p_internal_neg:.2f}$ kgf/m²):**
            * หน่วยแรงสุทธิรับลม: $p_{{net, w}} = {f['p_windward']:.2f} - ({p_internal_neg:.2f}) = {f['net_w_case1']:.2f}$ kgf/m²
            * หน่วยแรงสุทธิตามลม: $p_{{net, l}} = {p_leeward:.2f} - ({p_internal_neg:.2f}) = {net_l_case1:.2f}$ kgf/m²
            * **สูตรรวบแรงเฉือน:** $F_{{story}} = (p_{{net, w}} - p_{{net, l}}) \\times A_{{trib}} \\times 0.00980665$
            * แทนค่า: $F_{{story}} = ({f['net_w_case1']:.2f} - ({net_l_case1:.2f})) \\times {f['trib_area_front']:.1f} \\times 0.00980665 =$ **`{f['f_story_kn_c1']:.2f}` kN**
            
            **📌 ถอดสมการแปลงค่าแรงลัพธ์ประจำชั้น Case 2 (+ แรงดันภายในอาคาร $p_{{int+}} = {p_internal_pos:.2f}$ kgf/m²):**
            * หน่วยแรงสุทธิรับลม: $p_{{net, w}} = {f['p_windward']:.2f} - ({p_internal_pos:.2f}) = {f['net_w_case2']:.2f}$ kgf/m²
            * หน่วยแรงสุทธิตามลม: $p_{{net, l}} = {p_leeward:.2f} - ({p_internal_pos:.2f}) = {net_l_case2:.2f}$ kgf/m²
            * แทนค่า: $F_{{story}} = ({f['net_w_case2']:.2f} - ({net_l_case2:.2f})) \\times {f['trib_area_front']:.1f} \\times 0.00980665 =$ **`{f['f_story_kn_c2']:.2f}` kN**
            """)

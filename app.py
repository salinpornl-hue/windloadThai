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
# Streamlit UI Setup & Styling
# ==========================================
st.set_page_config(page_title="Wind Load Analyzer Pro | มยผ. 1311-50", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.3rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 25px; }
    .section-header { font-size: 1.4rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 15px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind Load Analyzer Pro (มยผ. 1311-50)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบวิเคราะห์แรงลมสุทธิ (Net Pressure) และแรงลัพธ์รวมรายชั้น (Story Force) สาหรับวิศวกรโครงสร้าง</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดและสเปกแรงลม")

st.sidebar.subheader("1. ข้อมูลสถานที่ตั้งและการ Auto-V")
prov_choice = st.sidebar.selectbox("พื้นที่ตั้งอาคาร (อ้างอิงความเร็วลมตามมาตรฐาน)", list(PROVINCE_V.keys()))

if "Manual Input" in prov_choice:
    V_input = st.sidebar.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
else:
    V_input = PROVINCE_V[prov_choice]
    st.sidebar.info(f"ระบบเลือกใช้ V = {V_input} m/s อัตโนมัติ")

exposure = st.sidebar.selectbox("สภาพภูมิประเทศ (Exposure Class)", ['A (พื้นที่โล่งแจ้ง/ชายฝั่ง)', 'B (พื้นที่ชานเมือง/มีต้นไม้หนาแน่น)', 'C (ในเมืองใหญ่/ตึกสูงหนาแน่น)'])
Iw_input = st.sidebar.selectbox("ค่าประกอบความสำคัญอาคาร (Iw)", [1.0, 1.15], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("2. สัมประสิทธิ์แรงดันภายนอกและภายใน")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อมของอาคาร", ["อาคารปิดทึบ (Enclosed Building)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)

# สัมประสิทธิ์แยกส่วนตามรูปทรงอาคารสี่เหลี่ยม
Cp_w = st.sidebar.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)
Cp_s = st.sidebar.number_input("Cp ผนังด้านข้าง (Sidewall)", value=-0.7, step=0.05)
Cp_r = st.sidebar.number_input("Cp หลังคาแบน (Flat Roof Uplift)", value=-0.7, step=0.05)

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

# --- [ENGINE CHECKER]: ตรวจสอบคุณสมบัติอาคารไหวตัวง่าย ---
slenderness = H_total / B
if H_total > 40.0 or slenderness > 4.0:
    st.warning(f"⚠️ **คำเตือนทางวิศวกรรม (มยผ. 1311-50):** อาคารนี้เข้าข่ายเป็น **'อาคารไหวตัวง่าย (Flexible Building)'** เนื่องจากความสูง H ({H_total:.2f} ม.) > 40 ม. หรือ อัตราส่วนความเพรียว H/B ({slenderness:.2f}) > 4 มาตรฐานกำหนดให้ต้องคำนวณค่าประกอบลมกระโชก ($C_g$) ด้วยวิธีพลศาสตร์อย่างละเอียด ห้ามตรึงค่าคงที่ที่ 2.0")

# ==========================================
# Engine Core Processing
# ==========================================
q = calculate_q(V_input)
Ce_H, Ce_H_exp = get_Ce_details(H_total, exposure)
qh = q * Ce_H

# แรงภายนอกและแรงภายใน (คงที่อิงตามความสูงยอดอาคาร H)
p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_roof_ext = Iw_input * qh * Cg_input * Cp_r
p_internal_pos = qh * GCpi     
p_internal_neg = qh * (-GCpi)  

# แรงลัพธ์สุทธิหลังคา
net_roof_case1 = p_roof_ext - p_internal_neg
net_roof_case2 = p_roof_ext - p_internal_pos

# แรงลัพธ์สุทธิฝั่งตามลม
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
    p_s_z = Iw_input * q * Ce_mid * Cg_input * Cp_s  # ผนังข้างภายนอก
    
    # คำนวณ Net Pressure รายชั้น
    net_w_case1 = p_w_z - p_internal_neg
    net_w_case2 = p_w_z - p_internal_pos
    
    net_s_case1 = p_s_z - p_internal_neg
    net_s_case2 = p_s_z - p_internal_pos
    
    # คำนวณ Story Force (แรงรวมกระทำรายชั้นเข้าสู่โครงสร้างหลัก)
    # F = (p_net_windward + |p_net_leeward|) * L_ตั้งฉากลม * h_floor
    f_story_kgf_c1 = (net_w_case1 + abs(net_l_case1)) * L * h_current
    f_story_kn_c1 = f_story_kgf_c1 * 0.00980665
    
    f_story_kgf_c2 = (net_w_case2 + abs(net_l_case2)) * L * h_current
    f_story_kn_c2 = f_story_kgf_c2 * 0.00980665
    
    floors_data.append({
        "floor_num": i + 1, "height": h_current, "z_bottom": z_bottom, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "Ce_exp": Ce_mid_exp, "p_windward": p_w_z, "p_sidewall_ext": p_s_z,
        "net_w_case1": net_w_case1, "net_w_case2": net_w_case2,
        "net_s_case1": net_s_case1, "net_s_case2": net_s_case2,
        "f_story_kn_c1": f_story_kn_c1, "f_story_kn_c2": f_story_kn_c2
    })
    z_cumulative = z_top

# ==========================================
# Helper Function: วาดลูกศรและกราฟิก
# ==========================================
def plot_building_wind(floors, view_mode):
    fig = go.Figure()
    
    # วาดตัวอาคาร
    fig.add_trace(go.Scatter(
        x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], 
        fill="toself", fillcolor="rgba(30, 58, 138, 0.05)", line=dict(color="#1E3A8A", width=3), name="โครงสร้าง"
    ))
    
    def add_arrow(x_wall, y_pos, val, is_windward):
        arrow_len = 1.5 + abs(val) / 30.0 
        if is_windward:
            if val >= 0:
                ax, ay, x, y = -arrow_len, y_pos, 0, y_pos
                color, text_pos = "#DC2626", "right"
            else:
                ax, ay, x, y = 0, y_pos, -arrow_len, y_pos
                color, text_pos = "#9333EA", "left"
        else:
            if val >= 0:
                ax, ay, x, y = B + arrow_len, y_pos, B, y_pos
                color, text_pos = "#DC2626", "left"
            else:
                ax, ay, x, y = B, y_pos, B + arrow_len, y_pos
                color, text_pos = "#EA580C", "right"
                
        fig.add_annotation(x=x, y=y, ax=ax, ay=ay, xref="x", yref="y", axref="x", ayref="y",
                           text=f"<b>{val:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowsize=1.2, 
                           arrowcolor=color, font=dict(color=color, size=10), xanchor=text_pos)

    # วาดแรงรายชั้นภายนอก/สุทธิ
    for f in floors:
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="rgba(75, 85, 99, 0.3)", width=1.5, dash="dash"))
        
        if view_mode == "External": val_w = f['p_windward']
        elif view_mode == "Case 1": val_w = f['net_w_case1']
        else: val_w = f['net_w_case2']
            
        add_arrow(x_wall=0, y_pos=f['z_mid'], val=val_w, is_windward=True)
        
        # เพิ่มป้ายแสดงค่า Story Force เป็นหัวลูกศรวิ่งเข้า Center ของชั้นนั้นๆ แทน
        f_force = f['f_story_kn_c1'] if view_mode == "Case 1" else f['f_story_kn_c2']
        if view_mode != "External":
            fig.add_annotation(x=B/2, y=f['z_mid'] + 0.4, text=f"📊 <b>F_story = {f_force:.1f} kN</b>",
                               showarrow=False, font=dict(color="#1D4ED8", size=10), bgcolor="white", opacity=0.85)

    if view_mode == "External": val_l = p_leeward
    elif view_mode == "Case 1": val_l = net_l_case1
    else: val_l = net_l_case2
        
    add_arrow(x_wall=B, y_pos=H_total/2, val=val_l, is_windward=False)

    # วาดลูกศรทิศทางแรงยกหลังคา (Flat Roof Uplift Suction)
    val_r = p_roof_ext if view_mode == "External" else (net_roof_case1 if view_mode == "Case 1" else net_roof_case2)
    fig.add_annotation(x=B/2, y=H_total + 1.5, ax=B/2, ay=H_total, xref="x", yref="y", axref="x", ayref="y",
                       text=f"<b>Roof Net: {val_r:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowcolor="#EF4444", font=dict(color="#EF4444", size=10))

    title_text = "แรงลมภายนอก (External Pressure)" if view_mode == "External" else f"แรงลมสุทธิ & โหลดรายชั้น {view_mode} (Net Pressure + Story Force)"
    fig.update_layout(
        title=dict(text=f"<b>แผนภาพอาคาร: {title_text}</b>", font=dict(size=14, color="#1E3A8A"), x=0.5),
        xaxis_title="ความกว้างอาคาร B (เมตร)", yaxis_title="ความสูง z (เมตร)", 
        yaxis_range=[-1, H_total + 3], xaxis_range=[-7, B + 7], height=500, margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="white", showlegend=False
    )
    fig.update_xaxes(showgrid=True, gridcolor='#E5E7EB')
    fig.update_yaxes(showgrid=True, gridcolor='#E5E7EB')
    return fig

# ==========================================
# TABS NAVIGATION
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 แดชบอร์ด & โมเดลจำลอง", "📑 เล่มรายการคำนวณอย่างละเอียด", "💾 ตารางโหลด ETABS/SAP2000 (Design Output)"])

# ------------------------------------------
# TAB 1: Dashboard
# ------------------------------------------
with tab1:
    st.markdown("#### 🎯 สรุปผลลัพธ์หลักหลักโครงสร้าง")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1: st.metric("ความสูงรวม (H)", f"{H_total:.2f} m")
    with m_col2: st.metric("แรงลมอ้างอิงพื้นฐาน (q)", f"{q:.2f} kgf/m²")
    with m_col3: st.metric("แรงลัพธ์ Story Force สูงสุด", f"{max([f['f_story_kn_c1'] for f in floors_data]):.1f} kN")
    with m_col4: st.metric("แรงยกสุทธิที่หลังคา (Roof)", f"{abs(net_roof_case1):.1f} kgf/m²")

    st.markdown("---")
    view_option = st.radio("เลือกกรณีโหลด (Load Case) เพื่อดูแผนภาพและพิกัดลูกศร:", 
                           ["External", "Case 1", "Case 2"], 
                           captions=["แรงลมภายนอก", "แรงลมสุทธิ + แรงดูดภายในอาคาร (-)", "แรงลมสุทธิ + แรงดันภายในอาคาร (+)"], horizontal=True)
    
    st.plotly_chart(plot_building_wind(floors_data, view_option), use_container_width=True)

# ------------------------------------------
# TAB 2: Calculation Report
# ------------------------------------------
with tab2:
    st.markdown("#### 📑 เล่มรายการคำนวณโครงสร้างอย่างเป็นสเต็ป (ส่งตรวจอนุมัติ)")
    st.markdown(f"""
    ### **[ส่วนที่ 1 - 3]: สเปกเริ่มต้นระบบ**
    * พื้นที่ทดสอบ: ความเร็วลมออกแบบอ้างอิง $V$ = `{V_input}` m/s $\\rightarrow$ $q$ = **`{q:.4f}` kgf/m²**
    * ตัวคูณประกอบและสสัมประสิทธิ์: $I_w$ = `{Iw_input}`, $C_g$ = `{Cg_input}`, $GC_{{pi}}$ = `±{GCpi:.2f}`
    * สัมประสิทธิ์รูปทรง $C_p$: Windward = `{Cp_w}`, Leeward = `{Cp_l}`, Sidewall = `{Cp_s}`, Flat Roof = `{Cp_r}`
    
    ---
    ### **[ส่วนที่ 4]: แรงลมแปรผันตามแนวความสูง**
    """)
    for f in floors_data:
        st.markdown(f"- **ชั้น {f['floor_num']} ($z = {f['z_mid']:.2f}$ ม.):** $C_e = {f['Ce']:.3f}$ $\\rightarrow$ $p_{{windward}} =$ `{f['p_windward']:.2f}` kgf/m² | $p_{{sidewall}} =$ `{f['p_sidewall_ext']:.2f}` kgf/m²")

    st.markdown(f"""
    ---
    ### **[ส่วนที่ 5]: โหลดควบคุมบริเวณหลังคาและผนังตามลม (คงที่ตลอดระดับความสูง)**
    * $C_e$ ที่ยอดอาคาร ($H = {H_total:.2f}$ ม.) = `{Ce_H:.3f}` $\\rightarrow$ $q_h = {qh:.2f}$ kgf/m²
    * **แรงลมภายนอกฝั่งตามลม (Leeward):** $p_l = {Iw_input} \\cdot {qh:.2f} \\cdot {Cg_input} \\cdot ({Cp_l}) =$ **`{p_leeward:.2f}` kgf/m²**
    * **แรงลมภายนอกบริเวณหลังคา (Roof Uplift):** $p_{{roof}} = {Iw_input} \\cdot {qh:.2f} \\cdot {Cg_input} \\cdot ({Cp_r}) =$ **`{p_roof_ext:.2f}` kgf/m²**
    * **แรงดันลมภายใน:** $p_{{int+}} =$ `{p_internal_pos:.2f}` kgf/m² | $p_{{int-}} =$ `{p_internal_neg:.2f}` kgf/m²
    """)
    
    st.markdown("---")
    st.markdown("### **[ส่วนที่ 6]: รายการคำนวณแรงสุทธิ (Net Pressure) และ แรงลัพธ์รวมรายชั้น (Story Force)**")
    st.markdown("สมการแรงรวมรายชั้น: $$F_{{story}} = (p_{{net, windward}} + |p_{{net, leeward}}|) \\times L \\times h_{{floor}}$$")
    
    for f in floors_data:
        with st.expander(f"🧮 รายละเอียดสูตรและการคำนวณของ: ชั้นที่ {f['floor_num']}", expanded=False):
            st.markdown(f"""
            **กรณีที่ 1: ผสมแรงดูดภายในอาคาร ($p_{{int-}} = {p_internal_neg:.2f}$ kgf/m²)**
            * $p_{{net, windward}}$ = ${f['p_windward']:.2f} - ({p_internal_neg:.2f}) =$ **`{f['net_w_case1']:.2f}` kgf/m²**
            * $p_{{net, leeward}}$ = ${p_leeward:.2f} - ({p_internal_neg:.2f}) =$ **`{net_l_case1:.2f}` kgf/m²**
            * $p_{{net, sidewall}}$ = ${f['p_sidewall_ext']:.2f} - ({p_internal_neg:.2f}) =$ **`{f['net_s_case1']:.2f}` kgf/m²**
            * **ถอดสมการหาแรงรวม Point Load (Case 1):**
              $$F = ({f['net_w_case1']:.2f} + |{net_l_case1:.2f}|) \\times {L} \\times {f['height']}$$
              $$F = {f['net_w_case1'] + abs(net_l_case1):.2f} \\times {L * f['height']:.2f} = { (f['net_w_case1'] + abs(net_l_case1)) * L * f['height'] :.2f} \\text{{ kgf}}$$
              $$\\mathbf{{F_{{story, Case1}} = {f['f_story_kn_c1']:.2f} \\text{{ kN}}}}$$
            
            **กรณีที่ 2: ผสมแรงดันภายในอาคาร ($p_{{int+}} = {p_internal_pos:.2f}$ kgf/m²)**
            * $p_{{net, windward}}$ = ${f['p_windward']:.2f} - ({p_internal_pos:.2f}) =$ **`{f['net_w_case2']:.2f}` kgf/m²**
            * $p_{{net, leeward}}$ = ${p_leeward:.2f} - ({p_internal_pos:.2f}) =$ **`{net_l_case2:.2f}` kgf/m²**
            * $p_{{net, sidewall}}$ = ${f['p_sidewall_ext']:.2f} - ({p_internal_pos:.2f}) =$ **`{f['net_s_case2']:.2f}` kgf/m²**
            * **ถอดสมการหาแรงรวม Point Load (Case 2):**
              $$\\mathbf{{F_{{story, Case2}} = {f['f_story_kn_c2']:.2f} \\text{{ kN}}}}$$
            """)

# ------------------------------------------
# TAB 3: Design Output & Export
# ------------------------------------------
with tab3:
    st.markdown("#### 💾 ตารางสรุปหน่วยแรงลมและการแปลงเป็น Point Load สำหรับคีย์เข้าโปรแกรมออกแบบโครงสร้าง")
    st.markdown("วิศวกรสามารถเลือก Copy คอลัมน์ **Story Force (kN)** ไปใส่ในตาราง Diaphragm หรือ Center of Mass ในโปรแกรม ETABS/SAP2000 ได้ทันที")
    
    summary_rows = []
    for f in floors_data:
        summary_rows.append({
            "Story": f"Floor {f['floor_num']}",
            "Net Windward C1 (kgf/m²)": round(f['net_w_case1'], 1),
            "Net Leeward C1 (kgf/m²)": round(net_l_case1, 1),
            "Net Sidewall C1 (kgf/m²)": round(f['net_s_case1'], 1),
            "🔥 Story Force C1 (kN)": round(f['f_story_kn_c1'], 2),
            "Net Windward C2 (kgf/m²)": round(f['net_w_case2'], 1),
            "Net Leeward C2 (kgf/m²)": round(net_l_case2, 1),
            "Net Sidewall C2 (kgf/m²)": round(f['net_s_case2'], 1),
            "🔥 Story Force C2 (kN)": round(f['f_story_kn_c2'], 2),
        })
        
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    # แสดงแรงลมหลังคาด้านบนสุด
    st.markdown(f"""
    <div style="background-color: #FFFBEB; padding: 15px; border-radius: 8px; border-left: 5px solid #F59E0B;">
    <strong>🏠 ข้อกำหนดโหลดแรงดันสุทธิที่บริเวณหลังคา (Roof Net Pressure):</strong><br>
    - <strong>Case 1 (+Internal Suction):</strong> <code>{net_roof_case1:.2f} kgf/m²</code> (แรงยกตัวขึ้นกระทำต่อแปและระบบแผ่นหลังคา)<br>
    - <strong>Case 2 (+Internal Pressure):</strong> <code>{net_roof_case2:.2f} kgf/m²</code> (แรงยกสุทธิสูงสุด วิกฤตที่สุดสำหรับออกแบบจุดยึดหลังคาเหล็ก)
    </div>
    """, unsafe_allow_html=True)
    
    csv_data = df_summary.to_csv(index=False).encode('utf-8-sig')
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(label="📥 ดาวน์โหลดตารางโหลดแยกรายชั้น (.csv)", data=csv_data, file_name="WindLoad_Pro_Output.csv", mime="text/csv")

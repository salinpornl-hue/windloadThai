import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# Core Logic & Math
# ==========================================
def calculate_q(V):
    """คำนวณหน่วยแรงลมอ้างอิง q = 0.5 * rho * V^2"""
    rho = 1.25 # ความหนาแน่นอากาศ
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665 # แปลงเป็น kgf/m^2

def get_Ce(z, exposure):
    """คำนวณ Ce อิงตาม Power Law"""
    z_eff = max(z, 6.0) # มยผ. กำหนดให้คิดความสูงขั้นต่ำที่ 6 เมตร
    if 'A' in exposure: return min(max((z_eff/10.0)**0.20, 0.9), 1.5)
    elif 'B' in exposure: return min(max((z_eff/10.0)**0.28, 0.7), 1.2)
    else: return min(max((z_eff/10.0)**0.40, 0.5), 1.0)

# ==========================================
# Streamlit UI Setup
# ==========================================
st.set_page_config(page_title="โปรแกรมคำนวณแรงลม มยผ. 1311-50", layout="wide")
st.title("🌪️ โปรแกรมคำนวณแรงลมและ Base Shear (มยผ. 1311-50)")
st.markdown("---")

# --- รับค่าตัวแปร ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📍 1. ข้อมูลสถานที่")
    V_input = st.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
    exposure = st.selectbox("สภาพภูมิประเทศ", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง)', 'C (เมือง/ตึกสูง)'], index=1)
    Iw_input = st.selectbox("ค่าประกอบความสำคัญ (Iw)", [1.0, 1.15])

with col2:
    st.markdown("### 🏢 2. มิติอาคาร (หลังคาแบน)")
    B = st.number_input("ความกว้างอาคารด้านขนานลม B (m)", value=15.0)
    L = st.number_input("ความยาวอาคารตั้งฉากลม L (m)", value=20.0)
    
    # เพิ่มการรับค่าจำนวนชั้นและความสูงแต่ละชั้น
    num_stories = st.number_input("จำนวนชั้นทั้งหมด", value=3, min_value=1, step=1)
    st.markdown("**ความสูงแต่ละชั้น (m):**")
    floor_cols = st.columns(min(num_stories, 4))
    floor_heights = []
    for i in range(num_stories):
        with floor_cols[i % 4]:
            h_val = st.number_input(f"ชั้น {i+1}", value=4.0 if i==0 else 3.5, min_value=1.0, key=f"h_{i}")
            floor_heights.append(h_val)

with col3:
    st.markdown("### 🌬️ 3. สภาพแวดล้อมอาคาร")
    enclosure = st.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
    Cg_input = st.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0)
    Cp_w = st.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8)
    Cp_l = st.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5)
    Cp_r = st.number_input("Cp หลังคาแบน (Roof Uplift)", value=-0.7)

# ตั้งค่า GCpi ตามประเภทอาคาร
GCpi = 0.55 if "Partially" in enclosure else 0.18

st.markdown("---")

if st.button("🚀 ประมวลผลและสร้างรายการคำนวณ", use_container_width=True):
    
    # ----------------------------------------
    # การคำนวณค่าทางวิศวกรรม
    # ----------------------------------------
    H_total = sum(floor_heights) # ความสูงตึกรวม
    q = calculate_q(V_input)
    Ce_H = get_Ce(H_total, exposure)
    qh = q * Ce_H
    
    # คำนวณแรงลมที่ความสูงหลังคา (สำหรับ Leeward, Roof และ Internal จะคงที่อิงยอดอาคาร)
    p_leeward = Iw_input * qh * Cg_input * Cp_l 
    p_roof = Iw_input * qh * Cg_input * Cp_r
    p_internal_pos = qh * GCpi
    p_internal_neg = qh * (-GCpi)
    
    floors_data = []
    z_cumulative = 0
    total_base_shear_kn = 0
    
    # วนลูปคำนวณแรงลมรับลม (Windward) แยกรายชั้น
    for i in range(num_stories):
        h = floor_heights[i]
        z_bottom = z_cumulative
        z_top = z_cumulative + h
        z_mid = (z_bottom + z_top) / 2.0
        
        Ce_mid = get_Ce(z_mid, exposure)
        p_w = Iw_input * q * Ce_mid * Cg_input * Cp_w
        
        # พื้นที่รับลม (Tributary Area) ของชั้นนี้ = ความยาวอาคาร * ความสูงชั้น
        trib_area = L * h
        
        # แรงรวมประจำชั้น (Story Force) 
        # เอาแรงอัดเข้าด้านหน้า (p_w) ลบด้วย แรงดูดออกด้านหลัง (p_leeward) ซึ่งเป็นค่าติดลบ ลบเจอลบกลายเป็นบวกทิศทางเดียวกัน
        story_force_kgf = (p_w - p_leeward) * trib_area 
        story_force_kn = story_force_kgf * 0.00980665 # แปลง kgf เป็น kN
        
        total_base_shear_kn += story_force_kn
        
        floors_data.append({
            "floor": i+1,
            "h": h,
            "z_bottom": z_bottom,
            "z_top": z_top,
            "z_mid": z_mid,
            "Ce": Ce_mid,
            "p_w": p_w,
            "trib_area": trib_area,
            "force_kn": story_force_kn
        })
        z_cumulative = z_top

    # ----------------------------------------
    # 1. แสดงรูปภาพประกอบอาคาร (Plotly) - จัดวางแนวตั้ง (กว้างเต็มจอ)
    # ----------------------------------------
    st.subheader("📐 1. แผนภาพหน่วยแรงดันลมบนหน้าตัดอาคาร (Cross Section View: kgf/m²)")
    
    fig1 = go.Figure()
    # วาดรูปร่างอาคาร 2D (เต็มกรอบ)
    fig1.add_trace(go.Scatter(
        x=[0, B, B, 0, 0], 
        y=[0, 0, H_total, H_total, 0], 
        fill="toself", fillcolor="rgba(240, 248, 255, 0.8)",
        line=dict(color="#1E3A8A", width=3), name="โครงสร้างอาคาร", showlegend=False
    ))
    
    # วาดเส้นแบ่งชั้นและลูกศร Windward
    for f in floors_data:
        fig1.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="gray", width=1.5, dash="dash"))
        
        # ลูกศร Windward (สีแดง) ปรับสเกลอัตโนมัติ
        arrow_start = -2 - (f['p_w']/30.0)
        fig1.add_annotation(x=0, y=f['z_mid'], ax=arrow_start, ay=f['z_mid'], xref="x", yref="y", axref="x", ayref="y",
                            text=f"<b>{f['p_w']:.1f}</b>", showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor="#DC2626", font=dict(color="#DC2626", size=13))
        
        # ป้ายชื่อชั้นกลางตัวตึก
        fig1.add_annotation(x=B/2, y=f['z_mid'], text=f"ชั้น {f['floor']} (h={f['h']}m)", showarrow=False, font=dict(color="#4B5563"))

    # วาดลูกศร Leeward (ด้านหลัง สีส้ม ค่าคงที่)
    fig1.add_annotation(x=B, y=H_total/2, ax=B+4, ay=H_total/2, xref="x", yref="y", axref="x", ayref="y",
                        text=f"<b>Leeward: {p_leeward:.1f}</b>", showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor="#EA580C", font=dict(color="#EA580C", size=13))
    
    # วาดลูกศร Roof (หลังคาแบน สีม่วง ชี้ขึ้น)
    fig1.add_annotation(x=B/2, y=H_total, ax=B/2, ay=H_total+2.5, xref="x", yref="y", axref="x", ayref="y",
                        text=f"<b>Roof Uplift: {p_roof:.1f} kgf/m²</b>", showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor="#9333EA", font=dict(color="#9333EA", size=13))
                           
    fig1.update_layout(xaxis_title="ความกว้างอาคาร B (m)", yaxis_title="ระดับความสูง z (m)", 
                       yaxis_range=[-1, H_total+3.5], xaxis_range=[-6, B+6], height=450, plot_bgcolor="white", margin=dict(t=30, b=30))
    fig1.update_xaxes(showgrid=True, gridcolor='#E5E7EB')
    fig1.update_yaxes(showgrid=True, gridcolor='#E5E7EB')
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("---")

    # แผนภาพที่ 2 อยู่ด้านล่าง กว้างเต็มจอ
    st.subheader("📐 2. ขอบเขตพื้นที่รับลมหน้าตรง (Elevation View - ด้านรับลม L)")
    
    fig2 = go.Figure()
    colors = ["#93C5FD", "#BFDBFE", "#DBEAFE"] # ไล่เฉดสีฟ้า
    
    for idx, f in enumerate(floors_data):
        c = colors[idx % len(colors)]
        fig2.add_trace(go.Scatter(
            x=[0, L, L, 0, 0], y=[f['z_bottom'], f['z_bottom'], f['z_top'], f['z_top'], f['z_bottom']],
            fill="toself", fillcolor=c, line=dict(color="#2563EB", width=2), showlegend=False
        ))
        # แสดงป้ายพื้นที่ชัดเจน
        fig2.add_annotation(x=L/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor']}: Area = {f['trib_area']:.1f} m²</b><br>(กว้าง {L}ม. × สูงช่วงชั้น {f['h']}ม.)", 
                            showarrow=False, font=dict(color="#1E3A8A", size=14))

    fig2.update_layout(xaxis_title="ความยาวหน้าแผงผนังรับแรง L (m)", yaxis_title="ระดับความสูง z (m)", 
                       yaxis_range=[-1, H_total+2], height=450, plot_bgcolor="white", margin=dict(t=30, b=30))
    fig2.update_xaxes(showgrid=True, gridcolor='#E5E7EB')
    fig2.update_yaxes(showgrid=True, gridcolor='#E5E7EB')
    st.plotly_chart(fig2, use_container_width=True)

    # ----------------------------------------
    # 2. รายการคำนวณ (Calculation Report)
    # ----------------------------------------
    st.markdown("---")
    st.subheader("📑 3. รายการคำนวณ (Calculation Report) และ Base Shear")
    
    st.success(f"### 💥 สรุปแรงเฉือนที่ฐานอาคาร (Total Base Shear): **{total_base_shear_kn:.2f} kN**")
    
    report_md = f"""
    **โครงการ:** คำนวณหน่วยแรงลมออกแบบระบบโครงสร้างหลัก (MWFRS) ตาม มยผ. 1311-50
    **ลักษณะอาคาร:** {enclosure}, ทรงสี่เหลี่ยมหลังคาแบน, กว้าง {B} ม., ยาว {L} ม., สูงรวม {H_total:.2f} ม. (จำนวน {num_stories} ชั้น)
    
    **1. ตัวแปรพื้นฐานและการคำนวณหน่วยแรงลมอ้างอิง ($q$)**
    * ความเร็วลมพื้นฐาน ($V$) = **{V_input} m/s**
    * ความหนาแน่นอากาศ ($\\rho$) = 1.25 $kg/m^3$
    * $q = \\frac{{0.5 \\cdot 1.25 \\cdot ({V_input})^2}}{{9.80665}}$ = **{q:.2f} $kgf/m^2$**
    
    **2. สัมประสิทธิ์ประกอบการออกแบบที่ยอดอาคาร (h = {H_total:.2f} ม.)**
    * สภาพภูมิประเทศ = **{exposure}** $\\rightarrow$ ค่าการเปิดโล่งที่ยอด ($C_{{e,h}}$) = **{Ce_H:.3f}**
    * $q_h = q \\times C_{{e,h}}$ = **{qh:.2f} $kgf/m^2$**
    * แรงลมภายนอกด้านตามลม (Leeward): $p_l = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_l}) =$ **{p_leeward:.2f} $kgf/m^2$**
    * แรงลมภายนอกหลังคาแบน (Roof): $p_r = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_r}) =$ **{p_roof:.2f} $kgf/m^2$**
    * แรงดันภายใน: $p_{{int+}}$ = **{p_internal_pos:.2f} $kgf/m^2$** | $p_{{int-}}$ = **{p_internal_neg:.2f} $kgf/m^2$**
    
    **3. การคำนวณแรงเฉือนฐานอาคาร (Base Shear Calculation)**
    แรงเฉือนฐานอาคารหาได้จากการเอา **แรงลมรับลมพัดเข้า ($p_w$)** หักลบด้วย **แรงลมตามลมที่ดูดออก ($p_l$)** (ลบเจอลบกลายเป็นบวก) จากนั้นนำไปคูณกับ **พื้นที่รับลมหน้าตรง ($A_{{trib}}$)** แยกทีละชั้น
    *สมการแปลงหน่วย:* $F_{{story}} = (p_w - p_l) \\times A_{{trib}} \\times 0.00980665$ (แปลง $kgf$ เป็น $kN$)
    """
    st.markdown(report_md)
    
    # แสดงการคำนวณ Base shear แจกแจงทีละชั้น
    for f in floors_data:
        st.markdown(f"""
        * **ชั้นที่ {f['floor']} (ความสูงช่วงชั้น {f['h']} ม.):**
          * ค่า $C_e$ ประจำชั้น = {f['Ce']:.3f} $\\rightarrow p_{{windward}} = {f['p_w']:.2f}$ $kgf/m^2$
          * พื้นที่รับลม $A_{{trib}}$ = กว้าง {L} ม. $\\times$ สูง {f['h']} ม. = **{f['trib_area']:.1f} $m^2$**
          * $F_{{{f['floor']}}} = ({f['p_w']:.2f} - ({p_leeward:.2f})) \\times {f['trib_area']:.1f} \\times 0.00980665$ = **{f['force_kn']:.2f} kN**
        """)
        
    st.markdown(f"""
    **สรุปผลรวมแรงเฉือนฐานอาคารสุทธิ (Total Base Shear - V):**
    $$V = \\sum F_{{story}} = {' + '.join([f"{f['force_kn']:.2f}" for f in floors_data])}$$
    $$V = \\mathbf{{{total_base_shear_kn:.2f} \\text{{ kN}}}}$$
    """)
    
    # ตารางสรุปโหลดเผื่อก๊อปปี้ไปวางใน Excel
    df = pd.DataFrame(floors_data)
    df = df[['floor', 'h', 'Ce', 'p_w', 'trib_area', 'force_kn']]
    df.columns = ['ชั้นที่', 'ความสูงชั้น (m)', 'Ce', 'Windward (kgf/m²)', 'Tributary Area (m²)', 'Story Force (kN)']
    st.dataframe(df, use_container_width=True, hide_index=True)

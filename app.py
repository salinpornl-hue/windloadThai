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
    z = max(z, 6.0) # ต่ำสุด 6 เมตรตาม มยผ.
    if 'A' in exposure: return min(max((z/10.0)**0.20, 0.9), 1.5)
    elif 'B' in exposure: return min(max((z/10.0)**0.28, 0.7), 1.2)
    else: return min(max((z/10.0)**0.40, 0.5), 1.0)

# ==========================================
# Streamlit UI Setup
# ==========================================
st.set_page_config(page_title="โปรแกรมคำนวณแรงลม มยผ. 1311-50 (อาคารหลายชั้น)", layout="wide")
st.title("🏢 โปรแกรมคำนวณแรงลมออกแบบ (มยผ. 1311-50) - อาคารหลังคาแบนหลายชั้น")
st.markdown("---")

# --- รับค่าตัวแปร ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📍 1. ข้อมูลสถานที่")
    V_input = st.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
    exposure = st.selectbox("สภาพภูมิประเทศ", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง)', 'C (เมือง/ตึกสูง)'])
    Iw_input = st.selectbox("ค่าประกอบความสำคัญ (Iw)", [1.0, 1.15])

with col2:
    st.markdown("### 🏢 2. มิติอาคาร")
    B = st.number_input("ความกว้างอาคารด้านขนานลม B (m)", value=15.0)
    L = st.number_input("ความยาวอาคารตั้งฉากลม L (m)", value=20.0)
    H = st.number_input("ความสูงอาคารรวม H (m)", value=15.0)
    num_stories = st.number_input("จำนวนชั้น", value=5, step=1, min_value=1)

with col3:
    st.markdown("### 🌬️ 3. สภาพแวดล้อมอาคาร")
    enclosure = st.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
    Cg_input = st.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0)
    Cp_w = st.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8)
    Cp_l = st.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5)

# ตั้งค่า GCpi ตามประเภทอาคาร
GCpi = 0.55 if "Partially" in enclosure else 0.18

st.markdown("---")

if st.button("🚀 ประมวลผลและสร้างรายการคำนวณ", use_container_width=True):
    
    # คำนวณค่าพื้นฐาน
    q = calculate_q(V_input)
    Ce_H = get_Ce(H, exposure) # Ce ที่ความสูงยอดอาคาร
    qh = q * Ce_H
    
    # ----------------------------------------
    # คำนวณแรงลมแยกตามชั้น (Windward Profile)
    # ----------------------------------------
    floor_height = H / num_stories
    floors_data = []
    
    for i in range(1, num_stories + 1):
        z = floor_height * i
        Ce_z = get_Ce(z, exposure)
        # แรงลมด้านรับลมแปรผันตามความสูง (z)
        p_w_z = Iw_input * q * Ce_z * Cg_input * Cp_w
        floors_data.append({
            "ชั้นที่": i,
            "ระดับความสูง z (m)": round(z, 2),
            "Ce (ผันแปรตามความสูง)": round(Ce_z, 3),
            "P_windward (kgf/m^2)": round(p_w_z, 2)
        })
        
    df_windward = pd.DataFrame(floors_data)
    
    # คำนวณแรงลมด้านอื่น ๆ (ด้านตามลมใช้ qh ที่ยอดอาคารคงที่)
    p_leeward = Iw_input * qh * Cg_input * Cp_l 
    p_internal_pos = qh * GCpi
    p_internal_neg = qh * (-GCpi)
    
    # ----------------------------------------
    # 1. แสดงรูปภาพประกอบอาคาร (Plotly)
    # ----------------------------------------
    st.subheader("📐 แผนภาพแรงลมจำลอง (Wind Pressure Schematic)")
    
    fig = go.Figure()
    # วาดรูปร่างอาคาร 2D (หลังคาแบน)
    fig.add_trace(go.Scatter(
        x=[0, B, B, 0, 0], 
        y=[0, 0, H, H, 0], 
        fill="toself", fillcolor="rgba(100, 150, 250, 0.2)",
        line=dict(color="blue", width=2), name="รูปด้านอาคาร"
    ))
    
    # วาดเส้นแบ่งชั้นอาคาร
    for i in range(1, num_stories):
        z = floor_height * i
        fig.add_shape(type="line", x0=0, y0=z, x1=B, y1=z,
                      line=dict(color="rgba(0,0,255,0.3)", width=1, dash="dash"))
    
    # วาดลูกศร Windward ไล่ตามระดับความสูง
    for i in range(1, num_stories + 1):
        z = floor_height * i - (floor_height/2) # วาดลูกศรตรงกลางชั้น
        # จำลองความยาวลูกศรให้แปรผันตามแรงดันนิดหน่อย (เพื่อความสวยงามในกราฟิก)
        arrow_length = 2 + (z/H)*4 
        fig.add_annotation(x=0, y=z, ax=-arrow_length, ay=z, xref="x", yref="y", axref="x", ayref="y",
                           text="Pw", showarrow=True, arrowhead=2, arrowsize=1.5, arrowcolor="red")
    
    # วาดลูกศร Leeward (ด้านหลัง ค่าคงที่)
    fig.add_annotation(x=B+4, y=H/2, ax=B, ay=H/2, xref="x", yref="y", axref="x", ayref="y",
                       text="Leeward (Constant)", showarrow=True, arrowhead=2, arrowsize=1.5, arrowcolor="orange")
                           
    fig.update_layout(xaxis_title="ความกว้าง B (m)", yaxis_title="ความสูง (m)", 
                      yaxis_range=[0, H+5], xaxis_range=[-8, B+8], height=500)
    st.plotly_chart(fig, use_container_width=True)

    # ----------------------------------------
    # 2. รายการคำนวณ (Calculation Report)
    # ----------------------------------------
    st.subheader("📑 รายการคำนวณ (Calculation Report)")
    
    st.markdown(f"""
    **โครงการ:** คำนวณหน่วยแรงลมออกแบบระบบโครงสร้างหลัก (MWFRS) ตาม มยผ. 1311-50
    **ลักษณะอาคาร:** {enclosure}, ทรงสี่เหลี่ยมหลังคาแบน, กว้าง **{B} ม.**, ยาว **{L} ม.**, สูงรวม **{H} ม.**, จำนวน **{num_stories} ชั้น**
    
    **1. ตัวแปรพื้นฐานและการคำนวณหน่วยแรงลมอ้างอิง ($q$)**
    * ความเร็วลมพื้นฐาน ($V$) = **{V_input} m/s**
    * ความหนาแน่นอากาศ ($\rho$) = 1.25 $kg/m^3$
    * $q = \\frac{{0.5 \cdot \rho \cdot V^2}}{{9.80665}}$ = **{q:.2f} $kgf/m^2$**
    
    **2. การคำนวณหน่วยแรงลมภายนอกด้านรับลม (Windward Pressure: $p_{{w}}$)**
    *สมการ:* $p_{{w}} = I_w \cdot q \cdot C_e \cdot C_g \cdot C_p$ 
    *(สำหรับอาคารหลายชั้น ค่า $C_e$ จะแปรผันตามความสูง $z$ ของแต่ละชั้น)*
    """)
    
    # แสดงตาราง DataFrame สำหรับ Windward
    st.dataframe(df_windward, use_container_width=True, hide_index=True)
    
    st.markdown(f"""
    **3. การคำนวณหน่วยแรงลมด้านอื่น ๆ (อ้างอิงความสูง $h$ ที่ยอดอาคาร = {H} ม.)**
    * ค่า $C_e$ ที่ยอดอาคาร = **{Ce_H:.3f}**
    * ค่า $q_h$ ที่ยอดอาคาร = **{qh:.2f} $kgf/m^2$**
    * **ผนังด้านตามลม (Leeward):** $p_{{l}} = {Iw_input} \cdot {qh:.2f} \cdot {Cg_input} \cdot ({Cp_l})$ = **{p_leeward:.2f} $kgf/m^2$** *(ค่าลบคือแรงดูดออก)*
      
    **4. การคำนวณหน่วยแรงลมภายใน (Internal Wind Pressure: $p_{{int}}$)**
    *สมการ:* $p_{{int}} = q_h \cdot GC_{{pi}}$
    * แรงดันบวก: $p_{{int+}} = {qh:.2f} \cdot {GCpi}$ = **{p_internal_pos:.2f} $kgf/m^2$**
    * แรงดูดลบ: $p_{{int-}} = {qh:.2f} \cdot (-{GCpi})$ = **{p_internal_neg:.2f} $kgf/m^2$**
    
    **5. สรุปการออกแบบ**
    ในการนำไปออกแบบโครงสร้างหลัก (MWFRS) ให้นำค่าแรงลมภายนอก $p_{{w}}$ (ที่แปรผันตามชั้นในตาราง) และ $p_{{l}}$ มาประกอบกับแรงลมภายใน $p_{{int}}$ ตามกรณีโหลด (Load Cases) เพื่อพิจารณาหาแรงกระทำสุทธิสูงสุดต่อไป
    """)

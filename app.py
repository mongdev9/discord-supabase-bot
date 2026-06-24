import streamlit as st
import os
from pypdf import PdfReader
from supabase import create_client
# ✨ เปลี่ยนวิธีการดึงคลังเครื่องมือใหม่เพื่อให้เซิร์ฟเวอร์ Cloud เข้าใจง่ายขึ้น
from google import genai
from google.genai import types
from dotenv import load_dotenv

# โหลดค่าคอนฟิกต่างๆ
load_dotenv()

# ตั้งค่าหน้าจอเว็บ
st.set_page_config(page_title="PM360 Document Uploader", page_icon="📄", layout="centered")

# เชื่อมต่อ Supabase และ Gemini API
@st.cache_resource
def init_connections():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    supabase_client = create_client(supabase_url, supabase_key)
    ai_client = genai.Client(api_key=gemini_key)  # ✨ เปลี่ยนมาใช้ตัวย่อใหม่ที่เชื่อมกันด้านบน
    return supabase_client, ai_client

try:
    supabase, ai_client = init_connections()
except Exception as e:
    st.error(f"❌ เชื่อมต่อระบบเบื้องหลังไม่สำเร็จ: {e}")

def get_embedding(text):
    """ฟังก์ชันแปลงข้อความเป็น Vector 3072 มิติ"""
    response = ai_client.models.embed_content(
        model="gemini-embedding-2",
        contents=text
    )
    return response.embeddings[0].values

# --- หน้าตา UI บนเว็บ ---
st.title("📄 ระบบอัปโหลดคู่มือเข้าสมองกลบอท")
st.write("อัปโหลดไฟล์ PDF เพื่ออัปเดตฐานข้อมูลให้บอทใน Discord ตอบได้ทันทีเพื่อน")

# กล่องลากวางไฟล์
uploaded_file = st.file_uploader("เลือกไฟล์คู่มือ PDF ของคุณที่นี่", type=["pdf"])

if uploaded_file is not None:
    file_name = uploaded_file.name
    st.info(f"📁 เจอไฟล์: {file_name} เรียบร้อยแล้ว")
    
    # ปุ่มกดสั่งลุย
    if st.button("🚀 เริ่มแปลงไฟล์เข้าฐานข้อมูล", type="primary"):
        try:
            with st.spinner("⏳ กำลังอ่านไฟล์และแปลง Vector... โปรดรอสักครู่"):
                # อ่านไฟล์ PDF จากหน่วยความจำ
                reader = PdfReader(uploaded_file)
                total_pages = len(reader.pages)
                
                progress_bar = st.progress(0)
                success_count = 0
                
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    
                    if text and text.strip():
                        # ล้างค่า \u0000 ขยะออกเหมือนในสคริปต์หลัก
                        cleaned_text = text.replace("\u0000", "")
                        
                        if cleaned_text.strip():
                            # แปลงเวกเตอร์
                            vector = get_embedding(cleaned_text)
                            
                            # ยิงเข้า Supabase
                            supabase.table("document_sections").insert({
                                "file_name": file_name,
                                "content": cleaned_text,
                                "embedding": vector
                            }).execute()
                            
                            success_count += 1
                    
                    # อัปเดตแถบเปอร์เซ็นต์หน้าเว็บ
                    progress_bar.progress((i + 1) / total_pages)
                
                st.success(f"✅ สำเร็จแล้วเพื่อน! อัปโหลดคู่มือเข้าคลังข้อมูลสำเร็จทั้งหมด {success_count} หน้า")
                
        except Exception as e:
            st.error(f"🚨 เกิดข้อผิดพลาดระหว่างอัปโหลด: {e}")

import time
import pandas as pd
import re
import json
from fuzzywuzzy import fuzz
import psycopg2
from datetime import datetime
from openai import OpenAI
from langchain_chroma import Chroma
from third_party.langchain_huggingface import HuggingFaceEmbeddings
import google.generativeai as genai
import numpy as np
from typing import Dict, Optional
import os
from memory import answer 

api_key ='api_key'

def write_to_db(user_query, bot_response):
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres.kwvpgdmmvilfzjikrplm",
        password="Tiendat2703",
        host="aws-0-ap-southeast-1.pooler.supabase.com",
        port=6543
    )
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memory (created_at, memory, memory_bot) VALUES (%s, %s, %s)",
        (datetime.now(), user_query, bot_response)
    )
    conn.commit()
    cur.close()
    conn.close()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, 'transform_filled_chitieu.xlsx')
df = pd.read_excel(file_path, engine='openpyxl')
university_list = df['Tên trường'].unique().tolist()
university_str = ', '.join(university_list)


# def rag(query):
#     embeded_model = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large-instruct",model_kwargs={"device": "cuda"})

#     chroma_db = Chroma(
#         embedding_function=embeded_model,
#         persist_directory="/Users/tiendat/Documents/NCKH_2025/chroma_db"
#     )
#     genai.configure(api_key="")
#     ctext = chroma_db.max_marginal_relevance_search(query, k=10, fetch_k=20)
#     context = "\n".join([doc.page_content for doc in ctext ])
#     #prompt = f"""hãy trả lời câu hỏi dựa vào:\n\n{context}\n\nCâu hỏi: {query}\n.Hãy trả lời câu hỏi như một người tư vấn và thật là dài và miêu tả rõ.\nTrả lời:"""
#     prompt = f"""
# <p><strong>📘 Dữ liệu nền:</strong></p>
# <pre>{context}</pre>

# <p><strong>❓ Câu hỏi:</strong> {query}</p>

# <p><strong>💬 Yêu cầu:</strong></p>
# <ul>
#     <li>Hãy trả lời một cách <strong>chi tiết, rõ ràng và dài</strong></li>
#     <li>Diễn đạt <strong>tự nhiên, có cảm xúc như người tư vấn thật</strong></li>
#     <li>Sử dụng <code>&lt;br&gt;</code> hoặc đoạn <code>&lt;p&gt;</code> để xuống dòng hợp lý</li>
# </ul>

# <p><strong>Trả lời (sử dụng định dạng HTML, đặc biệt là &lt;br&gt; để xuống dòng):</strong></p>
# """

#     model = genai.GenerativeModel("models/gemini-2.5-flash-preview-04-17")
#     response = model.generate_content(prompt, generation_config={"max_output_tokens": 10000})
#     return response.text
   # return f"<div>{response}</div>"
# query = "Tầm nhìn của Đại học Kinh tế ĐN"
# print(rag(query))



genai.configure(api_key="")

def gemini_extract(query: str):
    prompt = f"""Hãy phân tích câu hỏi sau và trích xuất thông tin theo các yêu cầu sau:

    - Trước tiên, nhận diện và chuyển các từ viết tắt thành dạng đầy đủ. Một số từ viết tắt phổ biến:
        + ĐH -> Đại học
        + CNTT -> Công nghệ thông tin
        + ĐN -> Đà Nẵng
        + HN -> Hà Nội
        + TPHCM hoặc HCM -> Thành phố Hồ Chí Minh
        + KHDL -> Khoa học dữ liệu
        + KT -> Kinh Tế
        + BK -> Bách Khoa
        + BKHN -> Bách Khoa Hà Nội
        + TMĐT -> Thương mại điện tử
        + HTTTQL -> Hệ thống thông tin quản lý
        + KDQT hoặc KTHN hoặc kthn -> Kinh doanh quốc tế
        + QTKD -> Quản trị kinh doanh
        + TKKT -> Thống kê kinh tế
        + KTQD -> Kinh tế quốc dân
        + ĐHQG -> Đại học Quốc Gia
      Nếu có từ viết tắt khác hoặc lỗi chính tả nhỏ, hãy suy luận ngữ nghĩa và chuyển thành dạng đúng nếu có thể (trừ khi lỗi quá nghiêm trọng).
    - Phân loại câu hỏi thành các loại sau (dựa trên ngữ nghĩa):
        + 'RAG': Nếu câu hỏi yêu cầu thông tin chi tiết về trường Đại học Kinh Tế Đà Nẵng (ví dụ: 'Giới thiệu về trường Đại học Kinh Tế Đà Nẵng', 'Chính sách học bổng của trường Đại học Kinh Tế Đà Nẵng', 'Lịch sử thành lập của Đại học Kinh Tế Đà Nẵng', 'Cơ sở vật chất của Đại học Kinh Tế Đà Nẵng', 'Học phí của Đại học Kinh Tế Đà Nẵng', v.v.).
        + 'search': Tìm kiếm thông tin cơ bản, bao gồm cả trường hợp tra cứu điểm chuẩn qua nhiều năm mà không yêu cầu phân tích xu hướng (ví dụ: 'Điểm chuẩn ngành Kế toán trường Đại học Kinh tế Đà Nẵng năm 2024?', 'Chỉ tiêu tuyển sinh ngành Kế toán trường Đại học Kinh tế Đà Nẵng?', 'Điểm chuẩn ngành Marketing trong 3 năm gần đây?' - vì đây là tra cứu điểm qua 3 năm, không phải phân tích xu hướng).
        + 'condition_search': Tìm kiếm theo điều kiện điểm chuẩn, chỉ tiêu tuyển sinh hoặc năm (ví dụ: 'Có ngành nào điểm dưới 25 không?', 'Các ngành có chỉ tiêu từ 50 đến 100?').
        + 'compare': Chỉ áp dụng khi câu hỏi rõ ràng yêu cầu so sánh giữa các trường, ngành, hoặc phương thức, thường đi kèm từ khóa 'so sánh' hoặc ngữ nghĩa yêu cầu so sánh rõ ràng (ví dụ: 'So sánh điểm ngành Kế Toán giữa trường Đại học Kinh Tế Đà Nẵng và trường Đại học Kinh Tế Quốc Dân', 'So sánh chỉ tiêu tuyển sinh ngành Kế toán giữa Đại học Kinh Tế Đà Nẵng và Đại học Bách Khoa Đà Nẵng').
        + 'trend_analysis': Chỉ áp dụng khi câu hỏi rõ ràng yêu cầu phân tích xu hướng hoặc biến động điểm chuẩn qua các năm, thường đi kèm từ khóa như 'xu hướng', 'biến động điểm', 'phân tích', 'sự thay đổi điểm' (ví dụ: 'Ngành Kế toán của trường Đại học Kinh tế Đà Nẵng có biến động điểm chuẩn lớn không qua các năm từ 2020 đến 2024?', 'Phân tích xu hướng điểm chuẩn của ngành Kế toán trường Đại học Kinh tế Đà Nẵng từ năm 2020 đến 2024.', 'Sự thay đổi điểm chuẩn ngành Kế toán qua các năm.'). Nếu chỉ tra cứu điểm qua nhiều năm mà không có ý phân tích, thì không phải là 'trend_analysis'.
        + 'highest_score': Tìm ngành/trường có điểm cao nhất khi chỉ hỏi 1 ngành mới được (ví dụ: 'Ngành có điểm cao nhất của trường Đại học Kinh Tế?', 'Ngành có điểm cao nhất?').
        + 'lowest_score': Tìm ngành/trường có điểm thấp nhất (ví dụ: 'Ngành có điểm thấp nhất của trường Đại học Kinh Tế?', 'Ngành Kế toán của trường nào thấp nhất?').
        + 'top_n': Tìm top N ngành/trường theo điểm chuẩn hoặc chỉ tiêu tuyển sinh (ví dụ: 'Top 5 ngành hàng đầu tại trường Bách Khoa Đà Nẵng', '3 trường có chỉ tiêu cao nhất về ngành Kế toán').
        + 'pass_chance': Kiểm tra khả năng đậu hoặc gợi ý trường/ngành phù hợp dựa trên điểm thi (ví dụ: 'Với 24 điểm, mình có thể đậu ngành Công nghệ Thông tin của trường Đại học Bách Khoa Đà Nẵng không?', 'Gợi ý trường phù hợp với 24 điểm').
        + 'ambiguous': Câu hỏi mơ hồ, thiếu thông tin (ví dụ: 'Điểm chuẩn đại học năm 2024?').
        + Nếu không xác định được, trả về 'unknown'.
        + Lưu ý: Phải phân tích kỹ ngữ nghĩa câu hỏi, không nhầm lẫn giữa 'search' và 'trend_analysis'. Ví dụ: 'Điểm chuẩn ngành Marketing trong 3 năm gần đây?' là 'search' vì mục đích là tra cứu điểm qua 3 năm, không phải phân tích xu hướng.
    - Nếu câu hỏi mơ hồ ('ambiguous'), trả về thông tin thiếu dưới dạng chuỗi (ví dụ: 'Tôi không xác định được trường hoặc ngành mà bạn đưa ra. Vui lòng cung cấp tên trường hoặc ngành cụ thể.').
    - Nếu câu hỏi có thông tin không hợp lệ (ví dụ: tổ hợp thi không tồn tại như 'ABC'), cập nhật missing_info để thông báo (ví dụ: 'Tổ hợp ABC không hợp lệ, vui lòng kiểm tra lại.').
    - Đại học:
        + Nếu có, trả về danh sách các tên đại học đầy đủ (ví dụ: ['Đại học Kinh tế Đà Nẵng', 'Đại học Bách Khoa Đà Nẵng']), không thêm từ 'trường', bỏ qua từ 'trường' nếu có.
        + Nếu không có, trả về null.
        + Nếu câu hỏi yêu cầu 'tất cả các trường', 'các trường', 'mọi trường', trả về 'all'.
        + Đặc biệt:
          - Nếu câu hỏi chỉ đề cập đến "Đại học Kinh Tế" mà không có thông tin bổ sung (ví dụ: không có "Quốc Dân", "Đà Nẵng",...), mặc định hiểu là "Đại học Kinh Tế Đà Nẵng".
          - Nếu câu hỏi chỉ đề cập đến "Đại học Bách Khoa" mà không có thông tin bổ sung (ví dụ: không có "Hà Nội", "Đà Nẵng", "Thành phố Hồ Chí Minh",...), mặc định hiểu là "Đại học Bách Khoa Đà Nẵng".
    - Ngành học:
        + Nếu có, trả về danh sách các tên ngành học đầy đủ (ví dụ: ['Khoa học dữ liệu', 'Kế toán']).
        + Nếu không có tên ngành cụ thể (chỉ có từ 'ngành' chung chung, ví dụ: 'Có ngành nào dưới 17 điểm không?'), trả về null.
        + Nếu câu hỏi yêu cầu 'tất cả các ngành', 'các ngành', 'mọi ngành', trả về 'all'.
        + Chỉ trích xuất ngành nếu câu hỏi có tên ngành cụ thể (ví dụ: 'Kế toán', 'Công nghệ Thông tin', 'Khoa học Dữ liệu',...).
    - Năm:
      + Đầu tiên, xác định xem câu hỏi có thông tin về năm hay không:
        - Nếu có từ 'năm' và giá trị số cụ thể (ví dụ: '2023', '2024'), trả về năm đó dưới dạng chuỗi (ví dụ: '2023').
        - Nếu có từ 'năm' nhưng yêu cầu 'tất cả các năm', 'qua các năm', 'mọi năm', hoặc các cụm từ tương tự, trả về 'all'.
        - Nếu có yêu cầu một khoảng năm liên tiếp (ví dụ: 'từ năm 2020 đến năm 2024', '2018 - 2024', '2020 đến 2024', 'qua các năm 2022,2023,2024'), trả về khoảng năm dưới dạng chuỗi 'start-end' (ví dụ: '2020-2024').
        - Nếu có yêu cầu các năm không liên tiếp (ví dụ: 'qua các năm 2020,2022,2023,2024', 'của năm 2018 và 2024'), trả về danh sách năm dưới dạng chuỗi, các năm cách nhau bằng dấu phẩy (ví dụ: '2020,2022,2023,2024').
        - Nếu có các cụm từ như 'các năm gần đây', 'một số năm gần đây', 'các năm về trước', trả về '2022,2023,2024' (coi như 3 năm gần đây hay 3 năm về trước tính từ 2024).
        - Nếu có cụm từ chứa số lượng năm kết hợp với 'gần đây' hoặc 'về trước' (ví dụ: '3 năm gần đây', '4 năm về trước'):
          - Tính từ năm hiện tại (2024) lùi lại theo số lượng năm được đề cập.
          - Ví dụ: '3 năm gần đây' -> '2022,2023,2024', '4 năm về trước' -> '2021,2022,2023,2024'.
        - Nếu có yêu cầu điều kiện năm (ví dụ: 'từ 2022 trở lên', 'sau 2022', 'trước 2022', '2022 trở xuống'), trả về điều kiện dưới dạng chuỗi trong year_condition (không trả về trong year):
          - 'year >= 2022' (từ 2022 trở lên).
          - 'year > 2022' (sau 2022).
          - 'year <= 2022' (2022 trở xuống).
          - 'year < 2022' (trước 2022).
      + Nếu không có thông tin về năm trong câu hỏi (không đề cập đến năm, không có cụm từ liên quan đến năm):
        - Nếu question_type là 'search' hoặc 'trend_analysis', trả về 'all' (để lọc theo tất cả các năm).
        - Với các question_type khác (như 'compare', 'pass_chance', 'highest_score', 'lowest_score', 'top_n', 'condition_search', 'ambiguous', 'unknown'), trả về '2024'.
    - Phương thức xét tuyển:
        + Nếu câu hỏi nói về 'Điểm chuẩn' hoặc 'Chỉ tiêu tuyển sinh' mà không có từ khóa cụ thể, trả về ['THPT Quốc gia'].
        + Nếu có từ khóa 'Học bạ', bao gồm 'Học bạ' trong danh sách (ví dụ: ['Học bạ']).
        + Nếu có từ khóa 'Đánh giá năng lực', 'DGNL', hoặc 'ĐGNL', bao gồm 'Đánh giá năng lực' trong danh sách.
        + Nếu có nhiều phương thức (ví dụ: 'điểm học bạ và điểm đánh giá năng lực'), trả về danh sách các phương thức (ví dụ: ['Học bạ', 'Đánh giá năng lực']).
        + Nếu yêu cầu 'tất cả các phương thức', 'mọi phương thức', trả về 'all'.
        + Nếu không xác định được, trả về null.
    - Thành phố:
        + Nếu có, trả về danh sách các tên thành phố (ví dụ: ['Đà Nẵng', 'Hà Nội']).
        + Nếu không có, trả về null.
        + Nếu yêu cầu 'tất cả các thành phố', 'các thành phố', 'mọi thành phố', trả về 'all'.
    - Điểm thi (dành cho câu hỏi pass_chance):
        - Nếu câu hỏi có chứa số thập phân hoặc số nguyên kèm theo từ 'điểm' (ví dụ: '24 điểm', '24.5 điểm'), trích xuất số đó dưới dạng số thực (float).
        - Nếu không có điểm thi, trả về null.
    - Điều kiện điểm chuẩn (nếu có):
        + Nếu câu hỏi yêu cầu tìm kiếm theo điều kiện điểm chuẩn, trả về điều kiện dưới dạng chuỗi:
          - 'score = 25' (điểm bằng 25).
          - 'score between 25 and 27' (điểm từ 25 đến 27).
          - 'score > 25' (trên 25).
          - 'score >= 25' (từ 25 trở lên).
          - 'score < 25' (dưới 25).
          - 'score <= 25' (từ 25 trở xuống).
          - 'score near 25 2' (xấp xỉ 25, sai số ±2).
          - Nếu không có điều kiện, trả về null.
    - Điều kiện chỉ tiêu tuyển sinh (nếu có):
        + Nếu câu hỏi yêu cầu tìm kiếm theo điều kiện chỉ tiêu tuyển sinh, trả về điều kiện dưới dạng chuỗi:
          - 'quota = 50' (chỉ tiêu bằng 50).
          - 'quota between 50 and 100' (chỉ tiêu từ 50 đến 100).
          - 'quota > 50' (trên 50).
          - 'quota >= 50' (từ 50 trở lên).
          - 'quota < 50' (dưới 50).
          - 'quota <= 50' (từ 50 trở xuống).
          - Nếu không có điều kiện, trả về null.
    - Tổ hợp thi (nếu có):
        + Nếu câu hỏi có yêu cầu về tổ hợp thi (ví dụ: 'Điểm chuẩn của tổ hợp A00', 'Chỉ tiêu tuyển sinh của tổ hợp A00,D01 và A01'), trả về danh sách các tổ hợp dưới dạng danh sách chuỗi (ví dụ: ['A00'], ['A00', 'D01', 'A01']).
        + Nếu tổ hợp không hợp lệ (ví dụ: 'ABC' không phải là tổ hợp thi hợp lệ), cập nhật missing_info để thông báo (ví dụ: 'Tổ hợp ABC không hợp lệ, vui lòng kiểm tra lại.').
        + Nếu không có yêu cầu về tổ hợp, trả về null.
        + Một số tổ hợp thi phổ biến để kiểm tra: A00, A01, B00, C00, D01, D03, D04, D06, D78, D96, v.v.
    - Top N (nếu có):
        + Nếu câu hỏi yêu cầu tìm top N với số cụ thể (ví dụ: 'Top 5 ngành hàng đầu tại trường Bách Khoa Đà Nẵng', '3 trường có chỉ tiêu cao nhất về ngành Kế toán'), trả về thông tin dưới dạng chuỗi:
          - 'top 5 major' (top 5 ngành).
          - 'top 3 university' (top 3 trường).
        + Nếu câu hỏi yêu cầu tìm top N nhưng không có số cụ thể (ví dụ: 'Các ngành hàng đầu tại trường Đại học Kinh tế Đà Nẵng', 'Các trường có chỉ tiêu cao nhất cho ngành Kế toán'), trả về:
          - 'top major' (các ngành hàng đầu).
          - 'top university' (các trường hàng đầu).
        + Nếu câu hỏi yêu cầu tìm bottom N với số cụ thể (ví dụ: '5 ngành có điểm thấp nhất tại trường Bách Khoa Đà Nẵng'), trả về:
          - 'bottom 5 major' (5 ngành thấp nhất).
          - 'bottom 3 university' (3 trường thấp nhất).
        + Nếu câu hỏi yêu cầu tìm bottom N nhưng không có số cụ thể (ví dụ: 'Các ngành điểm thấp nhất của trường Bách Khoa Đà Nẵng'), trả về:
          - 'bottom major' (các ngành thấp nhất).
          - 'bottom university' (các trường thấp nhất).
        + Nếu không có yêu cầu top N hoặc bottom N, trả về null.

    Câu hỏi: '{query}'

    Trả kết quả dưới dạng JSON với các keys: university, major, year, method, city, question_type, missing_info, score_condition, year_condition, top_n, score, quota, combinations.
    """

    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt, generation_config={"max_output_tokens": 10000})
    clean_response = response.text.strip().replace('```json', '').replace('```', '')
    data = json.loads(clean_response)

    # Kiểm tra thông tin thiếu cho trend_analysis
    if data['question_type'] == 'trend_analysis':
        missing_parts = []
        # Kiểm tra university
        if data['university'] is None or data['university'] == 'all':
            missing_parts.append('trường')
        # Kiểm tra major
        if data['major'] is None:
            missing_parts.append('ngành')
        # Kiểm tra year
        if data['year'] is None or data['year'] == 'all':
            missing_parts.append('năm')

        # Nếu có thông tin thiếu, đặt question_type thành 'ambiguous' và cập nhật missing_info
        if missing_parts:
            data['question_type'] = 'ambiguous'
            if len(missing_parts) == 3:
                data['missing_info'] = 'Mình cần thêm thông tin về trường, ngành và năm để phân tích xu hướng điểm chuẩn. Bạn có thể cung cấp thêm không?'
            elif len(missing_parts) == 2:
                data['missing_info'] = f'Mình cần thêm thông tin về {missing_parts[0]} và {missing_parts[1]} để phân tích xu hướng điểm chuẩn. Bạn có thể cung cấp thêm không?'
            else:
                data['missing_info'] = f'Mình cần thêm thông tin về {missing_parts[0]} để phân tích xu hướng điểm chuẩn. Bạn có thể cung cấp thêm không?'

    # Kiểm tra thông tin thiếu cho compare
    if data['question_type'] == 'compare':
        missing_parts = []
        # Kiểm tra university và major
        university_count = len(data['university']) if data['university'] and data['university'] != 'all' else 0
        major_count = len(data['major']) if data['major'] else 0

        # Chỉ đưa ra nhắc nhở nếu:
        if (university_count == 0 and major_count >= 2) or (major_count == 0 and university_count >= 2) or (university_count < 2 and major_count < 2):
            if university_count == 0:
                missing_parts.append('trường (cần ít nhất 2 trường để so sánh nếu không có ngành để so sánh)')
            else:
                missing_parts.append('ngành (cần ít nhất 2 ngành để so sánh nếu chỉ có 1 trường)')
            if major_count == 0:
                missing_parts.append('ngành')

        # Nếu có thông tin thiếu, đặt question_type thành 'ambiguous' và cập nhật missing_info
        if missing_parts:
            data['question_type'] = 'ambiguous'
            if len(missing_parts) == 2:
                data['missing_info'] = 'Mình cần thêm thông tin về trường (cần ít nhất 2 trường để so sánh nếu không có ngành để so sánh) và ngành để so sánh. Bạn có thể cung cấp thêm không?'
            else:
                data['missing_info'] = f'Mình cần thêm thông tin về {missing_parts[0]} để so sánh. Bạn có thể cung cấp thêm không?'

    print('Gemini Extract Output:', data)  # Debug
    return data

def check_pass_chance(df, user_score, university=None, major=None, year=None, method=None, original_df=None):
    # Kiểm tra điểm số hợp lệ, bỏ qua nếu method là "Đánh giá năng lực"
    if method and "đánh giá năng lực" not in [m.lower() for m in method]:
        if user_score < 0 or user_score > 40:
            return "Điểm thi không hợp lệ, vui lòng kiểm tra lại! Điểm thi phải nằm trong khoảng từ 0 đến 30."

    if university and university != 'all' and major:
        # Chuẩn hóa university và major trước khi so sánh
        university_cleaned = [clean_text(u.lower()) for u in university]
        major_cleaned = [clean_text(m.lower()) for m in major]

        if df['filtered_df'].empty:
            return f"Không tìm thấy dữ liệu cho các ngành {', '.join(major)} tại trường {', '.join(university)}{' năm ' + str(year) if year and year != 'all' else ''}."

        # Chuẩn hóa cột Tên trường và Tên Ngành trong DataFrame
        df_filtered = df['filtered_df']
        df_filtered = df_filtered[df_filtered['Tên trường'].str.lower().apply(clean_text).isin(university_cleaned)]
        df_filtered = df_filtered[df_filtered['Tên Ngành'].str.lower().apply(clean_text).isin(major_cleaned)]

        if year and year != 'all':
            if '-' in year:
                start_year, end_year = map(int, year.split('-'))
                df_filtered = df_filtered[(df_filtered['Năm'] >= start_year) & (df_filtered['Năm'] <= end_year)]
            elif ',' in year:
                years = [int(y) for y in year.split(',')]
                df_filtered = df_filtered[df_filtered['Năm'].isin(years)]
            else:
                df_filtered = df_filtered[df_filtered['Năm'] == int(year)]
        else:
            df_filtered = df_filtered[df_filtered['Năm'] == df_filtered['Năm'].max()]
        if method and method != 'all':
            df_filtered = df_filtered[df_filtered['Phương Thức Xét Tuyển'].str.lower().isin([m.lower() for m in method])]

        if df_filtered.empty:
            return f"Không tìm thấy dữ liệu cho các ngành {', '.join(major)} tại trường {', '.join(university)}{' năm ' + str(year) if year and year != 'all' else ''}."

        result = f"Dưới đây là các ngành phù hợp với {user_score} điểm tại trường {', '.join(university)}{' năm ' + str(df_filtered['Năm'].iloc[0]) if year != 'all' else ''}:\n"
        passable_majors = []
        for idx in df_filtered.index:
            row = original_df.loc[idx]  # Lấy giá trị từ bản gốc dựa trên index
            score = row['Điểm Chuẩn']
            method_text = f" (phương thức {row['Phương Thức Xét Tuyển']})" if method and method != 'all' else ""
            if user_score >= score:
                passable_majors.append(f"- Ngành {row['Tên Ngành']} tại trường {row['Tên trường']} với điểm chuẩn {score}{method_text}.")
        if passable_majors:
            result += "\n".join(passable_majors)
        else:
            result += "Không tìm thấy ngành nào phù hợp. Bạn có thể cân nhắc nguyện vọng khác!"
        return result

    if university and university != 'all' and not major:
        university_cleaned = [clean_text(u.lower()) for u in university]
        if df['filtered_df'].empty:
            return f"Không tìm thấy dữ liệu cho trường {', '.join(university)}{' năm ' + str(year) if year and year != 'all' else ''}."
        df_filtered = df['filtered_df']
        df_filtered = df_filtered[df_filtered['Tên trường'].str.lower().apply(clean_text).isin(university_cleaned)]

        if year and year != 'all':
            if '-' in year:
                start_year, end_year = map(int, year.split('-'))
                df_filtered = df_filtered[(df_filtered['Năm'] >= start_year) & (df_filtered['Năm'] <= end_year)]
            elif ',' in year:
                years = [int(y) for y in year.split(',')]
                df_filtered = df_filtered[df_filtered['Năm'].isin(years)]
            else:
                df_filtered = df_filtered[df_filtered['Năm'] == int(year)]
        else:
            df_filtered = df_filtered[df_filtered['Năm'] == df_filtered['Năm'].max()]
        if method and method != 'all':
            df_filtered = df_filtered[df_filtered['Phương Thức Xét Tuyển'].str.lower().isin([m.lower() for m in method])]

        if df_filtered.empty:
            return f"Không tìm thấy dữ liệu cho trường {', '.join(university)}{' năm ' + str(year) if year and year != 'all' else ''}."

        df_passable = df_filtered[df_filtered['Điểm Chuẩn'] <= user_score]
        if df_passable.empty:
            return f"Với {user_score} điểm, không tìm thấy ngành nào phù hợp tại trường {', '.join(university)}{' năm ' + str(year) if year and year != 'all' else ''}. Bạn có thể cân nhắc nguyện vọng khác!"

        result = f"Dưới đây là các ngành phù hợp với {user_score} điểm tại trường {', '.join(university)}{' năm ' + str(year) if year and year != 'all' else ''}:\n"
        for idx in df_passable.index:
            row = original_df.loc[idx]  # Lấy giá trị từ bản gốc dựa trên index
            method_text = f" (phương thức {row['Phương Thức Xét Tuyển']})" if method and method != 'all' else ""
            result += f"- Ngành {row['Tên Ngành']} tại trường {row['Tên trường']} với điểm chuẩn {row['Điểm Chuẩn']}{method_text}.\n"
        return result

    if major and (not university or university == 'all'):
        major_cleaned = [clean_text(m.lower()) for m in major]
        if df['filtered_df'].empty:
            return f"Không tìm thấy dữ liệu cho ngành {', '.join(major)}{' năm ' + str(year) if year and year != 'all' else ''}."
        df_filtered = df['filtered_df']
        df_filtered = df_filtered[df_filtered['Tên Ngành'].str.lower().apply(clean_text).isin(major_cleaned)]

        if year and year != 'all':
            if '-' in year:
                start_year, end_year = map(int, year.split('-'))
                df_filtered = df_filtered[(df_filtered['Năm'] >= start_year) & (df_filtered['Năm'] <= end_year)]
            elif ',' in year:
                years = [int(y) for y in year.split(',')]
                df_filtered = df_filtered[df_filtered['Năm'].isin(years)]
            else:
                df_filtered = df_filtered[df_filtered['Năm'] == int(year)]
        else:
            df_filtered = df_filtered[df_filtered['Năm'] == df_filtered['Năm'].max()]
        if method and method != 'all':
            df_filtered = df_filtered[df_filtered['Phương Thức Xét Tuyển'].str.lower().isin([m.lower() for m in method])]

        if df_filtered.empty:
            return f"Không tìm thấy dữ liệu cho ngành {', '.join(major)}{' năm ' + str(year) if year and year != 'all' else ''}."

        df_passable = df_filtered[df_filtered['Điểm Chuẩn'] <= user_score]
        if df_passable.empty:
            return f"Với {user_score} điểm, không tìm thấy trường nào phù hợp cho ngành {', '.join(major)}{' năm ' + str(year) if year and year != 'all' else ''}. Bạn có thể cân nhắc nguyện vọng khác!"

        result = f"Dưới đây là các trường phù hợp với {user_score} điểm cho ngành {', '.join(major)}{' năm ' + str(year) if year and year != 'all' else ''}:\n"
        for idx in df_passable.index:
            row = original_df.loc[idx]  # Lấy giá trị từ bản gốc dựa trên index
            method_text = f" (phương thức {row['Phương Thức Xét Tuyển']})" if method and method != 'all' else ""
            result += f"- Trường {row['Tên trường']} với ngành {row['Tên Ngành']} và điểm chuẩn {row['Điểm Chuẩn']}{method_text}.\n"
        return result

    if (not university or university == 'all') and not major:
        df_filtered = df['filtered_df'].copy()
        if df_filtered.empty:
            return f"Không tìm thấy dữ liệu{' năm ' + str(year) if year and year != 'all' else ''}."
        if year and year != 'all':
            if '-' in year:
                start_year, end_year = map(int, year.split('-'))
                df_filtered = df_filtered[(df_filtered['Năm'] >= start_year) & (df_filtered['Năm'] <= end_year)]
            elif ',' in year:
                years = [int(y) for y in year.split(',')]
                df_filtered = df_filtered[df_filtered['Năm'].isin(years)]
            else:
                df_filtered = df_filtered[df_filtered['Năm'] == int(year)]
        else:
            df_filtered = df_filtered[df_filtered['Năm'] == df_filtered['Năm'].max()]
        if method and method != 'all':
            df_filtered = df_filtered[df_filtered['Phương Thức Xét Tuyển'].str.lower().isin([m.lower() for m in method])]

        if df_filtered.empty:
            return f"Không tìm thấy dữ liệu{' năm ' + str(year) if year and year != 'all' else ''}."

        df_passable = df_filtered[df_filtered['Điểm Chuẩn'] <= user_score]
        if df_passable.empty:
            return f"Với {user_score} điểm, không tìm thấy ngành nào phù hợp{' năm ' + str(year) if year and year != 'all' else ''}. Bạn có thể cân nhắc nguyện vọng khác!"

        # Chỉ lấy tối đa 5 ngành bất kỳ có điểm chuẩn <= user_score
        df_passable = df_passable.sort_values(by='Điểm Chuẩn', ascending=False).head(5)
        result = f"Dưới đây là một số ngành/trường phù hợp với {user_score} điểm{' năm ' + str(year) if year and year != 'all' else ''}:\n"
        for idx in df_passable.index:
            row = original_df.loc[idx]  # Lấy giá trị từ bản gốc dựa trên index
            method_text = f" (phương thức {row['Phương Thức Xét Tuyển']})" if method and method != 'all' else ""
            result += f"- Ngành {row['Tên Ngành']} tại trường {row['Tên trường']} với điểm chuẩn {row['Điểm Chuẩn']}{method_text}.\n"
        return result

# Hàm phụ để lọc theo điểm chuẩn
def filter_by_score(df, score_condition=None, top_n=None, question_type=None, major=None):
    if not score_condition and not top_n and question_type not in ['highest_score', 'lowest_score']:
        return df

    # Xử lý các điều kiện điểm chuẩn
    if score_condition:
        if 'score =' in score_condition:
            value = float(score_condition.split('=')[1].strip())
            df = df[df['Điểm Chuẩn'] == value]
        elif 'score between' in score_condition:
            start, end = map(float, score_condition.split('between')[1].split('and'))
            df = df[(df['Điểm Chuẩn'] >= start) & (df['Điểm Chuẩn'] <= end)]
        elif 'score >' in score_condition:
            threshold = float(score_condition.split('>')[1].strip())
            df = df[df['Điểm Chuẩn'] > threshold]
        elif 'score >=' in score_condition:
            threshold = float(score_condition.split('>=')[1].strip())
            df = df[df['Điểm Chuẩn'] >= threshold]
        elif 'score <' in score_condition:
            threshold = float(score_condition.split('<')[1].strip())
            df = df[df['Điểm Chuẩn'] < threshold]
        elif 'score <=' in score_condition:
            threshold = float(score_condition.split('<=')[1].strip())
            df = df[df['Điểm Chuẩn'] <= threshold]
        elif 'score near' in score_condition:
            parts = score_condition.split()
            value = float(parts[2])
            tolerance = float(parts[3])
            df = df[(df['Điểm Chuẩn'] >= value - tolerance) & (df['Điểm Chuẩn'] <= value + tolerance)]

    # Xử lý trường hợp điểm cao nhất
    if question_type == 'highest_score':
        if major:
            df = df[df['Tên Ngành'].str.lower() == major[0].lower()]
        if df.empty:
            return df
        # Sắp xếp theo Điểm Chuẩn giảm dần, tiêu chí phụ là Tên Ngành tăng dần
        df = df.sort_values(by=['Điểm Chuẩn', 'Tên Ngành'], ascending=[False, True])
        df = df.head(1)  # Lấy ngành/trường có điểm cao nhất

    # Xử lý trường hợp điểm thấp nhất
    if question_type == 'lowest_score':
        if major:
            df = df[df['Tên Ngành'].str.lower() == major[0].lower()]
        if df.empty:
            return df
        # Sắp xếp theo Điểm Chuẩn tăng dần, tiêu chí phụ là Tên Ngành tăng dần
        df = df.sort_values(by=['Điểm Chuẩn', 'Tên Ngành'], ascending=[True, True])
        df = df.head(1)  # Lấy ngành/trường có điểm thấp nhất

    # Xử lý trường hợp top N hoặc bottom N
    if top_n:
        # Xác định số lượng N (mặc định là 5 nếu không có số cụ thể)
        if top_n in ['top major', 'top university', 'bottom major', 'bottom university']:
            n = 5  # Mặc định lấy 5 nếu không có số cụ thể
        else:
            n = int(top_n.split()[1])

        # Xử lý top N ngành/trường
        if 'top' in top_n:
            if 'major' in top_n:
                # Top N ngành (cao nhất)
                df = df.sort_values(by=['Điểm Chuẩn', 'Tên Ngành'], ascending=[False, True])
                df = df.head(n)
            elif 'university' in top_n:
                # Top N trường (cao nhất)
                if major:
                    df = df[df['Tên Ngành'].str.lower() == major[0].lower()]
                if df.empty:
                    return df
                df = df.sort_values(by=['Điểm Chuẩn', 'Tên trường'], ascending=[False, True])
                df = df.head(n)

        # Xử lý bottom N ngành/trường
        elif 'bottom' in top_n:
            if 'major' in top_n:
                # Bottom N ngành (thấp nhất)
                df = df.sort_values(by=['Điểm Chuẩn', 'Tên Ngành'], ascending=[True, True])
                df = df.head(n)
            elif 'university' in top_n:
                # Bottom N trường (thấp nhất)
                if major:
                    df = df[df['Tên Ngành'].str.lower() == major[0].lower()]
                if df.empty:
                    return df
                df = df.sort_values(by=['Điểm Chuẩn', 'Tên trường'], ascending=[True, True])
                df = df.head(n)

    return df

# Hàm phụ để lọc theo năm
def filter_by_year(df, year=None, year_condition=None):
    if not year and not year_condition:
        return df

    # Xử lý điều kiện năm cụ thể
    if year and year != 'all':
        if '-' in year:
            start_year, end_year = map(int, year.split('-'))
            df = df[(df['Năm'] >= start_year) & (df['Năm'] <= end_year)]
        elif ',' in year:
            years = [int(y) for y in year.split(',')]
            df = df[df['Năm'].isin(years)]
        else:
            df = df[df['Năm'] == int(year)]
        return df

    # Xử lý điều kiện năm logic
    if year_condition:
        if 'year >=' in year_condition:
            threshold = int(year_condition.split('>=')[1].strip())
            df = df[df['Năm'] >= threshold]
        elif 'year >' in year_condition:
            threshold = int(year_condition.split('>')[1].strip())
            df = df[df['Năm'] > threshold]
        elif 'year <=' in year_condition:
            threshold = int(year_condition.split('<=')[1].strip())
            df = df[df['Năm'] <= threshold]
        elif 'year <' in year_condition:
            threshold = int(year_condition.split('<')[1].strip())
            df = df[df['Năm'] < threshold]

    return df

# Hàm phụ để loại bỏ nội dung trong ngoặc tròn
def clean_text(text):
    if pd.isna(text) or not text:
        return text
    return re.sub(r'\([^()]*\)', '', text).strip()

def search_action(query, info=None):
    # Nếu info không được truyền vào, gọi gemini_extract (dự phòng)
    if info is None:
        info = gemini_extract(query)

    # Đọc dữ liệu từ file Excel và lưu bản sao gốc
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(BASE_DIR, 'transform_filled_chitieu.xlsx')
    original_df = pd.read_excel(file_path, engine='openpyxl')
    df = original_df.copy()  # Bản sao để chuẩn hóa

    # Chuẩn hóa dữ liệu trong DataFrame để so sánh
    df['Tên trường'] = df['Tên trường'].str.lower().str.replace(r'[-–]', ' ', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()
    df['Tên Ngành'] = df['Tên Ngành'].str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()
    df['Phương Thức Xét Tuyển'] = df['Phương Thức Xét Tuyển'].str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()
    df['Thành phố'] = df['Thành phố'].str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()
    # Chuẩn hóa cột Tổ hợp (nếu có)
    if 'Tổ hợp' in df.columns:
        df['Tổ hợp'] = df['Tổ hợp'].str.upper().str.replace(r'\s+', '', regex=True).str.strip()

    # Chuẩn hóa thông tin từ JSON
    university = info.get('university', None)
    if university and university != 'all':
        university = [u.lower().strip() for u in university]
        if len(university) == 1 and university[0] == 'đại học':
            university = None
    major = info.get('major', None)
    if major and major != 'all':
        major = [m.lower().strip() for m in major]
    year = info.get('year', '2024')
    year_condition = info.get('year_condition', None)
    method = info.get('method', None)
    if method and method != 'all':
        method = [m.lower().strip() for m in method]
    city = info.get('city', None)
    if city:
        city = [c.lower().strip() for c in city]
    score_condition = info.get('score_condition', None)
    quota_condition = info.get('quota', None)  # Điều kiện chỉ tiêu tuyển sinh
    combinations = info.get('combinations', None)  # Danh sách tổ hợp thi
    question_type = info.get('question_type', 'search')
    top_n = info.get('top_n', None)

    # Hàm tính độ tương đồng cho danh sách, bỏ qua nội dung trong ngoặc tròn
    def match_score_list(text, targets, threshold=80):
        if pd.isna(text) or not text or not targets:
            return False
        if targets == 'all':
            return True

        # Loại bỏ nội dung trong ngoặc tròn từ text và target
        text_cleaned = clean_text(text)
        for target in targets:
            target_cleaned = clean_text(target)
            score = fuzz.ratio(text_cleaned, target_cleaned)
            if score >= threshold:
                return True
        return False

    # Lọc theo năm trước tiên và tạo bản sao rõ ràng
    df_filtered = filter_by_year(df, year, year_condition).copy()

    # Lọc theo tổ hợp thi (nếu có)
    if combinations:
        # Chuẩn hóa tổ hợp trong câu hỏi
        combinations = [c.upper().strip() for c in combinations]
        # Lọc các dòng có chứa ít nhất một trong các tổ hợp
        pattern = '|'.join(combinations)
        df_filtered = df_filtered[df_filtered['Tổ hợp'].str.contains(pattern, na=False, case=False)]
        # Ưu tiên các dòng có Chỉ tiêu tuyển sinh không null
        df_filtered = df_filtered.sort_values(by='Chỉ tiêu tuyển sinh', na_position='last')

    # Lọc DataFrame bằng fuzzy matching
    # Nếu university là None, không lọc theo trường
    df_filtered['university_match'] = True if not university else df_filtered['Tên trường'].apply(lambda x: match_score_list(x, university))
    # Nếu major là None, không lọc theo ngành
    df_filtered['major_match'] = True if not major else df_filtered['Tên Ngành'].apply(lambda x: match_score_list(x, major))
    df_filtered['method_match'] = df_filtered['Phương Thức Xét Tuyển'].apply(lambda x: match_score_list(x, method))

    # Lọc các hàng khớp
    df_filtered = df_filtered[df_filtered['university_match'] & df_filtered['major_match'] & df_filtered['method_match']]
    print("After fuzzy matching:", df_filtered.to_string(index=False, justify='left'))

    # Nếu có thành phố, lọc theo cột Thành phố
    if city:
        df_filtered = df_filtered[df_filtered['Thành phố'].apply(lambda x: any(c in x for c in city if pd.notna(x)))]

    # Lọc theo điểm chuẩn
    df_filtered = filter_by_score(df_filtered, score_condition, top_n, question_type, major)
    print("After filtering by score:", df_filtered.to_string(index=False, justify='left'))

    # Lọc theo chỉ tiêu tuyển sinh (nếu có)
    if quota_condition:
        # Chỉ lọc các dòng có Chỉ tiêu tuyển sinh không null
        df_filtered = df_filtered[df_filtered['Chỉ tiêu tuyển sinh'].notnull()]
        if quota_condition.startswith('quota ='):
            value = int(quota_condition.split('=')[1].strip())
            df_filtered = df_filtered[df_filtered['Chỉ tiêu tuyển sinh'] == value]
        elif quota_condition.startswith('quota between'):
            start, end = map(int, quota_condition.split('between')[1].split('and'))
            df_filtered = df_filtered[(df_filtered['Chỉ tiêu tuyển sinh'] >= start) & (df_filtered['Chỉ tiêu tuyển sinh'] <= end)]
        elif quota_condition.startswith('quota >'):
            value = int(quota_condition.split('>')[1].strip())
            df_filtered = df_filtered[df_filtered['Chỉ tiêu tuyển sinh'] > value]
        elif quota_condition.startswith('quota >='):
            value = int(quota_condition.split('>=')[1].strip())
            df_filtered = df_filtered[df_filtered['Chỉ tiêu tuyển sinh'] >= value]
        elif quota_condition.startswith('quota <'):
            value = int(quota_condition.split('<')[1].strip())
            df_filtered = df_filtered[df_filtered['Chỉ tiêu tuyển sinh'] < value]
        elif quota_condition.startswith('quota <='):
            value = int(quota_condition.split('<=')[1].strip())
            df_filtered = df_filtered[df_filtered['Chỉ tiêu tuyển sinh'] <= value]

    # Xử lý top N hoặc highest_score/lowest_score cho chỉ tiêu tuyển sinh
    if top_n and 'quota' in top_n:
        if top_n.startswith('top'):
            ascending = False
            df_filtered = df_filtered[df_filtered['Chỉ tiêu tuyển sinh'].notnull()]
            df_filtered = df_filtered.sort_values(by='Chỉ tiêu tuyển sinh', ascending=ascending)
            if 'major' in top_n:
                df_filtered = df_filtered.groupby(['Tên Ngành']).first().reset_index()
            else:  # university
                df_filtered = df_filtered.groupby(['Tên trường']).first().reset_index()
            if top_n.startswith('top '):
                n = int(top_n.split()[1])
                df_filtered = df_filtered.head(n)
        elif top_n.startswith('bottom'):
            ascending = True
            df_filtered = df_filtered[df_filtered['Chỉ tiêu tuyển sinh'].notnull()]
            df_filtered = df_filtered.sort_values(by='Chỉ tiêu tuyển sinh', ascending=ascending)
            if 'major' in top_n:
                df_filtered = df_filtered.groupby(['Tên Ngành']).first().reset_index()
            else:  # university
                df_filtered = df_filtered.groupby(['Tên trường']).first().reset_index()
            if top_n.startswith('bottom '):
                n = int(top_n.split()[1])
                df_filtered = df_filtered.head(n)

    if question_type != 'pass_chance' and question_type != 'RAG':
        # Xử lý các trường hợp đặc biệt (nếu không có top_n hoặc highest_score)
        if not top_n and question_type not in ['highest_score']:
            # Trường hợp không chỉ định trường và ngành
            if (not university or university == 'all') and (not major or major == 'all'):
                limit = 20 if university == 'all' and major == 'all' else 25  # Nếu cả hai là 'all', lấy top 20
                df_filtered = df_filtered.sort_values(by='Điểm Chuẩn', ascending=False)
                df_filtered = df_filtered.groupby(['Tên trường', 'Tên Ngành']).first().reset_index()
                df_filtered = df_filtered.head(limit)

            # Trường hợp không chỉ định trường (university là null hoặc 'all')
            elif not university or university == 'all':
                limit = 20 if university == 'all' else 25  # Nếu university là 'all', lấy top 20 trường
                if '-' in str(year) or ',' in str(year):
                    if '-' in str(year):
                        _, end_year = map(int, str(year).split('-'))
                    else:
                        end_year = max([int(y) for y in str(year).split(',')])
                    temp_df = df_filtered[df_filtered['Năm'] == end_year]
                    temp_df = temp_df.sort_values(by='Điểm Chuẩn', ascending=False)
                    top_schools = temp_df.groupby('Tên trường').first().reset_index().head(limit)['Tên trường'].tolist()
                    df_filtered = df_filtered[df_filtered['Tên trường'].isin(top_schools)]
                else:
                    df_filtered = df_filtered.sort_values(by='Điểm Chuẩn', ascending=False)
                    df_filtered = df_filtered.groupby('Tên trường').first().reset_index()
                    df_filtered = df_filtered.head(limit)

            # Trường hợp không chỉ định ngành (major là null hoặc 'all')
            elif not major or major == 'all':
                # Nếu major là 'all' và có university cụ thể, lấy top 20 ngành của trường đó
                if university and university != 'all':
                    # Nếu không có university cụ thể, logic xử lý giống như trước
                    limit = 25 if major == 'all' else 25  # Nếu major là 'all', lấy top 20 ngành; nếu major là None, lấy top 5
                    if '-' in str(year) or ',' in str(year):
                        if '-' in str(year):
                            _, end_year = map(int, str(year).split('-'))
                        else:
                            end_year = max([int(y) for y in str(year).split(',')])
                        temp_df = df_filtered[df_filtered['Năm'] == end_year]
                        temp_df = temp_df.sort_values(by='Điểm Chuẩn', ascending=False)
                        top_majors = temp_df.groupby('Tên Ngành').first().reset_index().head(limit)['Tên Ngành'].tolist()
                        df_filtered = df_filtered[df_filtered['Tên Ngành'].isin(top_majors)]
                    else:
                        df_filtered = df_filtered.sort_values(by='Điểm Chuẩn', ascending=False)
                        df_filtered = df_filtered.groupby('Tên Ngành').first().reset_index()
                        df_filtered = df_filtered.head(limit)
                else:
                    # Sắp xếp theo điểm chuẩn giảm dần, nhóm theo ngành và lấy top 20 ngành
                    df_filtered = df_filtered.sort_values(by='Điểm Chuẩn', ascending=False)
                    df_filtered = df_filtered.groupby('Tên Ngành').first().reset_index()
                    df_filtered = df_filtered.head(20)  # Lấy top 20 ngành của trường

            # Trường hợp câu hỏi loại 'search' với 2 trường hoặc 2 ngành trở lên
            elif question_type == 'search' and ((university and len(university) >= 2) or (major and len(major) >= 2)):
                # Đảm bảo có ít nhất 1 dòng cho mỗi trường/ngành (nếu có dữ liệu)
                temp_df = df_filtered.copy()
                temp_df = temp_df.sort_values(by='Điểm Chuẩn', ascending=False)

                # Nếu có 2 trường trở lên
                if university and len(university) >= 2:
                    university_cleaned = [clean_text(u.lower()) for u in university]
                    final_df = pd.DataFrame()  # DataFrame cuối cùng
                    for uni in university_cleaned:
                        # Lấy ít nhất 1 dòng cho mỗi trường (nếu có dữ liệu)
                        uni_df = temp_df[temp_df['Tên trường'].str.lower().apply(clean_text) == uni]
                        if not uni_df.empty:
                            uni_df = uni_df.head(1)  # Lấy dòng đầu tiên (điểm cao nhất)
                            final_df = pd.concat([final_df, uni_df])
                    if not final_df.empty:
                        df_filtered = final_df
                    else:
                        # Nếu không có dữ liệu cho trường nào, giữ nguyên df_filtered
                        df_filtered = temp_df.head(5)

                # Nếu có 2 ngành trở lên
                elif major and len(major) >= 2:
                    major_cleaned = [clean_text(m.lower()) for m in major]
                    final_df = pd.DataFrame()
                    for maj in major_cleaned:
                        # Lấy ít nhất 1 dòng cho mỗi ngành (nếu có dữ liệu)
                        maj_df = temp_df[temp_df['Tên Ngành'].str.lower().apply(clean_text) == maj]
                        if not maj_df.empty:
                            maj_df = maj_df.head(1)  # Lấy dòng đầu tiên (điểm cao nhất)
                            final_df = pd.concat([final_df, maj_df])
                    if not final_df.empty:
                        df_filtered = final_df
                    else:
                        # Nếu không có dữ liệu cho ngành nào, giữ nguyên df_filtered
                        df_filtered = temp_df.head(5)

            # Trường hợp question_type là 'compare', không áp dụng logic lọc thêm
            elif question_type == 'compare':
                # Giữ nguyên df_filtered sau khi lọc bằng fuzzy matching và score
                df_filtered = df_filtered.sort_values(by='Điểm Chuẩn', ascending=False)
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(BASE_DIR, f'static/media/{query}.xlsx')
        df_filtered.to_excel(file_path, engine='openpyxl')

    print("Final result:", df_filtered.to_string(index=False, justify='left'))
    return {'filtered_df': df_filtered, 'original_df': original_df}  # Trả về cả DataFrame đã lọc và bản gốc

def do_nothing():
    return None


def answer_question(question, search_results, info):
    client = OpenAI(api_key= api_key)

    # Kiểm tra nếu search_results là thông báo lỗi (chuỗi)
    if isinstance(search_results, str):
        return search_results

    # Kiểm tra loại câu hỏi để xử lý search_results phù hợp
    question_type = info.get('question_type', 'unknown')

    # Xử lý cho trend_analysis (search_results là chuỗi)
    if question_type == 'trend_analysis':
        if isinstance(search_results, str):
            # search_results đã là chuỗi từ analyze_trend, trả về trực tiếp
            missing_data_info = info.get('missing_data_info', '')
            reminder = ""
            university_missing = info.get('university') is None or info.get('university') == 'all'
            major_missing = info.get('major') is None
            if university_missing and major_missing:
                reminder = "\nMình nhận thấy câu hỏi của bạn chưa có thông tin cụ thể về trường và ngành. Nếu bạn cung cấp thêm thông tin về trường và ngành cụ thể hơn, mình có thể trả lời chi tiết và chính xác hơn đấy!"
            elif university_missing:
                reminder = "\nMình nhận thấy câu hỏi của bạn chưa có thông tin cụ thể về trường. Nếu bạn cung cấp thêm tên trường cụ thể, mình có thể trả lời chi tiết hơn nhé!"
            elif major_missing:
                reminder = "\nMình nhận thấy câu hỏi của bạn chưa có thông tin cụ thể về ngành. Nếu bạn cung cấp thêm tên ngành cụ thể, mình có thể trả lời chi tiết hơn nhé!"
            return f"Mình đã phân tích xu hướng điểm chuẩn: \n{search_results}{missing_data_info}{reminder}"
        else:
            return "Kết quả phân tích xu hướng không hợp lệ. Vui lòng kiểm tra lại dữ liệu hoặc câu hỏi."

    # Kiểm tra xem DataFrame có dữ liệu không (nếu search_results là DataFrame)
    if not isinstance(search_results, str) and search_results.empty:
        missing_data_info = info.get('missing_data_info', '')
        return f"Mình không tìm thấy thông tin phù hợp. Bạn có thể cung cấp thêm thông tin về trường hoặc ngành học để mình hỗ trợ tốt hơn nhé!{missing_data_info}"

    # Kiểm tra xem DataFrame có thiếu cột cần thiết không (nếu search_results là DataFrame)
    if not isinstance(search_results, str) and ('Tên trường' not in search_results.columns or 'Tên Ngành' not in search_results.columns or 'Điểm Chuẩn' not in search_results.columns):
        missing_data_info = info.get('missing_data_info', '')
        return f"Dữ liệu không đầy đủ thông tin về trường, ngành hoặc điểm chuẩn. Mình cần thêm thông tin để trả lời chính xác hơn, bạn có thể cung cấp thêm nhé!{missing_data_info}"

    # Kiểm tra xem câu hỏi có thiếu thông tin về university hoặc major không
    university_missing = info.get('university') is None or info.get('university') == 'all'
    major_missing = info.get('major') is None

    # Chuẩn bị lời nhắc nhở nếu thiếu thông tin (trừ trường hợp pass_chance đã xử lý)
    reminder = ""
    if info.get('question_type') != 'pass_chance':
        if university_missing and major_missing:
            reminder = "\nMình nhận thấy câu hỏi của bạn chưa có thông tin cụ thể về trường và ngành. Nếu bạn cung cấp thêm thông tin về trường và ngành, mình có thể trả lời chi tiết và chính xác hơn đấy!"
        elif university_missing:
            reminder = "\nMình nhận thấy câu hỏi của bạn chưa có thông tin cụ thể về trường. Nếu bạn cung cấp thêm tên trường, mình có thể trả lời chi tiết hơn nhé!"
        elif major_missing:
            reminder = "\nMình nhận thấy câu hỏi của bạn chưa có thông tin cụ thể về ngành. Nếu bạn cung cấp thêm tên ngành, mình có thể trả lời chi tiết hơn nhé!"

    # Lấy thông tin về dữ liệu thiếu (nếu có)
    missing_data_info = info.get('missing_data_info', '')

    # Nếu DataFrame không rỗng, bỏ qua missing_data_info (vì đã tìm thấy dữ liệu)
    if not search_results.empty:
        missing_data_info = ""

    # Kiểm tra giá trị chỉ tiêu tuyển sinh trước khi gọi LLM
    quota_info = "Không có dữ liệu"
    if 'Chỉ tiêu tuyển sinh' in search_results.columns:
        # Lấy giá trị chỉ tiêu tuyển sinh (nếu có)
        quota_value = search_results['Chỉ tiêu tuyển sinh'].iloc[0] if not search_results.empty else None
        if pd.notna(quota_value):
            quota_info = str(quota_value)
        else:
            quota_info = "Không có dữ liệu"

    # Nếu search_results là chuỗi (từ check_pass_chance hoặc compare_advanced), trả lời trực tiếp
    if isinstance(search_results, str):
        if search_results.startswith("Mình không thể") or search_results.startswith("Không tìm thấy"):
            return search_results + reminder
        return f"Mình đã kiểm tra và đây là những gì mình tìm được: {search_results}{missing_data_info}Bạn có muốn mình kiểm tra thêm thông tin khác không?" + reminder

    prompt = f"""Bạn là một trợ lý AI thân thiện, được thiết kế để giúp người dùng với giọng điệu tự nhiên, giống như đang trò chuyện với một người bạn. Dựa trên câu hỏi, loại câu hỏi (từ info['question_type']), và dữ liệu được cung cấp, hãy trả lời một cách rõ ràng, dễ hiểu, và hữu ích.

**Câu hỏi:** {question}
**Dữ liệu (DataFrame):** {search_results.to_string(index=False, justify='left')}
**Loại câu hỏi (question_type):** {info.get('question_type', 'unknown')}
**Điểm người dùng (nếu có):** {info.get('score', 'Không có')}
**Điều kiện chỉ tiêu tuyển sinh (nếu có):** {info.get('quota', 'Không có')}
**Tổ hợp thi (nếu có):** {info.get('combinations', 'Không có')}
**Giá trị Chỉ tiêu tuyển sinh (nếu có):** {quota_info}

**Hướng dẫn trả lời:**
- Trả lời bằng văn bản thuần túy, không sử dụng ký hiệu định dạng như **, *, hoặc Markdown. Ví dụ: thay vì "Ngành **Kế toán**", hãy dùng "Ngành Kế toán".
- **Xử lý thang điểm đặc biệt:**
    - Điểm chuẩn thường nằm trong thang điểm 0-30 (đặc biệt với phương thức THPT Quốc gia). Tuy nhiên, một số ngành/trường có thang điểm 40, dẫn đến điểm chuẩn trong khoảng 31-40.
    - Khi trả lời, nếu điểm chuẩn nằm trong khoảng 31-40, hãy thêm ghi chú trong dấu ngoặc: "(thang điểm 40)". Ví dụ: "ngành Công nghệ thông tin ở trường Đại học Kinh tế Quốc dân, với điểm chuẩn là 35.17 (thang điểm 40)".
    - Nếu điểm chuẩn từ 0-30, không cần thêm ghi chú (coi như thang điểm 30 mặc định).
- **Hiển thị thông tin Chỉ tiêu tuyển sinh (nếu có):**
    - Nếu câu hỏi yêu cầu thông tin về chỉ tiêu tuyển sinh (dựa trên câu hỏi hoặc loại câu hỏi), sử dụng giá trị từ "Giá trị Chỉ tiêu tuyển sinh" được cung cấp ở trên.
    - Nếu giá trị Chỉ tiêu tuyển sinh là "Không có dữ liệu", thông báo: "Chỉ tiêu tuyển sinh cho ngành này hiện tại không có dữ liệu."
    - Ví dụ: Nếu giá trị Chỉ tiêu tuyển sinh là "55.0", trả lời: "Chỉ tiêu tuyển sinh cho ngành này là 55.0."
- **Hiển thị thông tin Tổ hợp thi (nếu có):**
    - Nếu câu hỏi yêu cầu thông tin theo tổ hợp thi (dựa trên cột "Tổ hợp" trong DataFrame), hiển thị danh sách tổ hợp thi tương ứng (cột "Tổ hợp").
    - Nếu không có tổ hợp phù hợp, dựa vào thông tin từ missing_info (nếu có) để thông báo.
- **Đối với câu hỏi loại 'search' (ví dụ: 'Điểm chuẩn ngành Kế toán trường Đại học Kinh tế Đà Nẵng?', 'Chỉ tiêu tuyển sinh ngành Kế toán trường Đại học Kinh tế Đà Nẵng?'):
    - Dữ liệu là DataFrame. Trả về danh sách các ngành/trường kèm Tên trường, Tên ngành, Điểm chuẩn, Chỉ tiêu tuyển sinh (dựa trên giá trị đã cung cấp), Năm cụ thể và Tổ hợp thi (nếu có).
    - Ví dụ: "Mình tìm thấy ngành Kế toán của trường Đại học Kinh tế Đà Nẵng có điểm chuẩn 24.25, chỉ tiêu tuyển sinh là 50, vào năm 2024, áp dụng cho các tổ hợp D01, D03."
- Đối với câu hỏi loại 'condition_search' (ví dụ: 'Có ngành Kế toán nào dưới 25 điểm không?'):
    - Dữ liệu là DataFrame đã được lọc theo điều kiện điểm chuẩn (score_condition). Trả về danh sách các ngành/trường thỏa mãn điều kiện.
    - Ví dụ: "Mình tìm thấy một số ngành Kế Toán có điểm chuẩn dưới 25 điểm như sau: Ngành Kế Toán của trường Đại học Kinh Tế Đà Nẵng có điểm chuẩn 24.25."
- Đối với câu hỏi loại 'top_n' hoặc 'bottom_n' (ví dụ: 'Top 5 ngành hàng đầu tại trường Bách Khoa Đà Nẵng'):
    - Dữ liệu là DataFrame. Trả về danh sách theo định dạng: "Mình đã tìm được một số ngành hàng đầu tại trường [Tên trường] (theo điểm chuẩn) cho năm [Năm] như sau nhé:"
      - 1. Ngành [Tên ngành] của trường [Tên trường] với điểm chuẩn [Điểm chuẩn] (thêm ghi chú thang điểm nếu cần).
      - 2. ...
    - Nếu dựa trên chỉ tiêu tuyển sinh: "Mình đã tìm được một số ngành có chỉ tiêu cao nhất tại trường [Tên trường] cho năm [Năm] như sau nhé:"
- Sử dụng ngôn ngữ thân thiện, tự nhiên: "Mình đã kiểm tra và đây là những gì mình tìm được:", hoặc "Mình tìm thấy một số thông tin phù hợp với câu hỏi của bạn như sau:".
- Thêm gợi ý phù hợp (nếu có): "Nếu bạn có điểm số cụ thể, mình có thể gợi ý trường phù hợp hơn nhé!" hoặc "Bạn có muốn mình so sánh thêm phương thức khác không?".
- Nếu không có dữ liệu phù hợp, trả lời: "Mình không tìm thấy thông tin phù hợp với yêu cầu của bạn. Bạn có thể cung cấp thêm chi tiết (như trường, ngành, hoặc năm) để mình hỗ trợ tốt hơn không?"

## ĐẦU RA:

- Toàn bộ câu trả lời phải được format bằng HTML, nằm gọn trong một `<div>` chính.
- Các phần có thể tổ chức dạng `<p>`, `<ul>`, `<li>`, có thể thêm `<strong>` để nhấn mạnh Tên trường/Tên ngành.

Ví dụ mẫu trả lời HTML:

<div>
  <p>Mình tìm thấy thông tin như sau:</p>
  <ul>
    <li>Ngành Công nghệ Thông tin tại Đại học Kinh tế Đà Nẵng có điểm chuẩn 24.25.</li>
    <li>Chỉ tiêu tuyển sinh: 50.</li>
    <li>Tổ hợp xét tuyển: D01, A00.</li>
  </ul>
  <p>Nếu bạn muốn mình gợi ý thêm các trường phù hợp khác, cứ cho mình biết nhé!</p>
</div>
"""

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'user', 'content': prompt},
        ]
    )
    return response.choices[0].message.content + missing_data_info + reminder

# Các hàm phụ trong reasoning_step
def compare_advanced(df, university=None, major=None, year=None, method=None, original_df=None, question=None):
    # Kiểm tra thông tin đầu vào
    if not university or len(university) < 2:
        return "Mình cần thêm thông tin về trường (cần ít nhất 2 trường để so sánh) để so sánh. Bạn có thể cung cấp thêm không?"
    if not major:
        return "Mình cần thêm thông tin về ngành để so sánh. Bạn có thể cung cấp thêm không?"

    # Chuẩn hóa dữ liệu để lọc
    university_cleaned = [clean_text(u.lower()) for u in university]
    major_cleaned = [clean_text(m.lower()) for m in major]
    method_cleaned = [m.lower() for m in method] if method and method != 'all' else None

    # Lọc DataFrame
    df_filtered = df['filtered_df']
    df_filtered = df_filtered[df_filtered['Tên trường'].str.lower().apply(clean_text).isin(university_cleaned)]
    df_filtered = df_filtered[df_filtered['Tên Ngành'].str.lower().apply(clean_text).isin(major_cleaned)]

    if year and year != 'all':
        if '-' in year:
            start_year, end_year = map(int, year.split('-'))
            df_filtered = df_filtered[(df_filtered['Năm'] >= start_year) & (df_filtered['Năm'] <= end_year)]
        elif ',' in year:
            years = [int(y) for y in year.split(',')]
            df_filtered = df_filtered[df_filtered['Năm'].isin(years)]
        else:
            df_filtered = df_filtered[df_filtered['Năm'] == int(year)]
    else:
        df_filtered = df_filtered[df_filtered['Năm'] == df_filtered['Năm'].max()]

    if method_cleaned:
        df_filtered = df_filtered[df_filtered['Phương Thức Xét Tuyển'].str.lower().isin(method_cleaned)]

    if df_filtered.empty:
        return f"Không tìm thấy dữ liệu để so sánh cho các ngành {', '.join(major)} tại trường {', '.join(university)}{' năm ' + str(year) if year and year != 'all' else ''}{' theo phương thức ' + ', '.join(method) if method and method != 'all' else ''}."

    # Nhóm dữ liệu theo ngành, trường, phương thức, năm
    grouped = df_filtered.groupby(['Tên Ngành', 'Tên trường', 'Phương Thức Xét Tuyển', 'Năm'])[['Điểm Chuẩn', 'Chỉ tiêu tuyển sinh']].first().reset_index()

    if grouped.empty:
        return f"Không tìm thấy dữ liệu phù hợp để so sánh cho các ngành {', '.join(major)} tại trường {', '.join(university)}{' năm ' + str(year) if year and year != 'all' else ''}{' theo phương thức ' + ', '.join(method) if method and method != 'all' else ''}."

    # Ánh xạ tên trường và ngành từ original_df
    name_mapping = {}
    if original_df is not None:
        for _, row in original_df.iterrows():
            uni_cleaned = clean_text(row['Tên trường'].lower())
            major_cleaned = clean_text(row['Tên Ngành'].lower())
            method_cleaned = row['Phương Thức Xét Tuyển'].lower()
            key = (uni_cleaned, major_cleaned, method_cleaned)
            name_mapping[key] = {
                'Tên trường': row['Tên trường'],
                'Tên Ngành': row['Tên Ngành'],
                'Phương Thức Xét Tuyển': row['Phương Thức Xét Tuyển']
            }

    # Xử lý thang điểm và so sánh
    result = f"Mình đã kiểm tra{' năm ' + str(year) if year and year != 'all' else ''}:\n"
    scale_warning = False
    # Kiểm tra nếu question không được truyền vào, mặc định so sánh điểm chuẩn
    compare_quota = False if question is None else 'chỉ tiêu tuyển sinh' in question.lower()

    # Kiểm tra dữ liệu thiếu trước khi so sánh
    missing_data_info = []
    for m in major:
        for meth in (method if method and method != 'all' else ['THPT Quốc gia']):
            subset = grouped[(grouped['Tên Ngành'].str.lower().apply(clean_text) == clean_text(m.lower())) &
                            (grouped['Phương Thức Xét Tuyển'].str.lower() == meth.lower())]
            found_universities = subset['Tên trường'].str.lower().apply(clean_text).unique().tolist()
            missing_universities = [u for u in university if clean_text(u.lower()) not in found_universities]
            if missing_universities:
                missing_data_info.append(f"Mình không tìm thấy dữ liệu về ngành {m} theo phương thức {meth} của trường {', '.join(missing_universities)}, nên không thể so sánh đầy đủ được.")

    # Nhóm theo ngành và phương thức để so sánh
    for major in grouped['Tên Ngành'].unique():
        for method in grouped['Phương Thức Xét Tuyển'].unique():
            # Lọc dữ liệu cho ngành và phương thức hiện tại
            subset = grouped[(grouped['Tên Ngành'] == major) & (grouped['Phương Thức Xét Tuyển'] == method)]

            if len(subset) < 1:  # Không có dữ liệu
                continue

            # Lấy tên ngành và phương thức hiển thị từ original_df
            display_major = major
            display_method = method
            if original_df is not None and len(subset) > 0:
                row = subset.iloc[0]
                uni_cleaned = clean_text(row['Tên trường'].lower())
                major_cleaned = clean_text(row['Tên Ngành'].lower())
                method_cleaned = row['Phương Thức Xét Tuyển'].lower()
                key = (uni_cleaned, major_cleaned, method_cleaned)
                if key in name_mapping:
                    display_major = name_mapping[key]['Tên Ngành']
                    display_method = name_mapping[key]['Phương Thức Xét Tuyển']

            # Kiểm tra thang điểm (nếu so sánh điểm chuẩn)
            scales = []
            if not compare_quota:
                for _, row in subset.iterrows():
                    score = row['Điểm Chuẩn']
                    scale = 40 if 31 <= score <= 40 else 30
                    scales.append(scale)

            # Liệt kê thông tin (điểm chuẩn hoặc chỉ tiêu tuyển sinh)
            if compare_quota:
                result += f"Ngành {display_major} theo phương thức {display_method} có chỉ tiêu tuyển sinh như sau:\n"
                for _, row in subset.iterrows():
                    uni_cleaned = clean_text(row['Tên trường'].lower())
                    major_cleaned = clean_text(row['Tên Ngành'].lower())
                    method_cleaned = row['Phương Thức Xét Tuyển'].lower()
                    key = (uni_cleaned, major_cleaned, method_cleaned)

                    # Lấy tên trường hiển thị từ original_df
                    display_university = row['Tên trường']
                    if key in name_mapping:
                        display_university = name_mapping[key]['Tên trường']

                    quota = row['Chỉ tiêu tuyển sinh']
                    if pd.isna(quota):
                        result += f"- {display_university}: Chỉ tiêu tuyển sinh hiện tại không có dữ liệu.\n"
                    else:
                        result += f"- {display_university}: {int(quota)} sinh viên.\n"

                    # So sánh chỉ tiêu nếu có ít nhất 2 trường
                    if len(subset) >= 2:
                        subset_with_quota = subset[subset['Chỉ tiêu tuyển sinh'].notnull()]
                        if len(subset_with_quota) >= 2:
                            row1 = subset_with_quota.iloc[0]
                            row2 = subset_with_quota.iloc[1]
                            quota1 = row1['Chỉ tiêu tuyển sinh']
                            quota2 = row2['Chỉ tiêu tuyển sinh']
                            uni_cleaned1 = clean_text(row1['Tên trường'].lower())
                            uni_cleaned2 = clean_text(row2['Tên trường'].lower())
                            major_cleaned = clean_text(row1['Tên Ngành'].lower())
                            method_cleaned = row1['Phương Thức Xét Tuyển'].lower()

                            school1 = row1['Tên trường']
                            school2 = row2['Tên trường']
                            if (uni_cleaned1, major_cleaned, method_cleaned) in name_mapping:
                                school1 = name_mapping[(uni_cleaned1, major_cleaned, method_cleaned)]['Tên trường']
                            if (uni_cleaned2, major_cleaned, method_cleaned) in name_mapping:
                                school2 = name_mapping[(uni_cleaned2, major_cleaned, method_cleaned)]['Tên trường']

                            diff = abs(quota1 - quota2)
                            higher_school = school1 if quota1 > quota2 else school2
                            result += f"=> Chênh lệch giữa hai trường là {diff:.0f} sinh viên, {higher_school} có chỉ tiêu cao hơn.\n"
                        else:
                            result += "Một số trường không có dữ liệu chỉ tiêu, nên mình không thể so sánh đầy đủ được.\n"
            else:
                result += f"Ngành {display_major} theo phương thức {display_method} có điểm chuẩn như sau:\n"
                for _, row in subset.iterrows():
                    uni_cleaned = clean_text(row['Tên trường'].lower())
                    major_cleaned = clean_text(row['Tên Ngành'].lower())
                    method_cleaned = row['Phương Thức Xét Tuyển'].lower()
                    key = (uni_cleaned, major_cleaned, method_cleaned)

                    # Lấy tên trường hiển thị từ original_df
                    display_university = row['Tên trường']
                    if key in name_mapping:
                        display_university = name_mapping[key]['Tên trường']

                    score = row['Điểm Chuẩn']
                    scale = 40 if 31 <= score <= 40 else 30
                    scale_text = " (thang điểm 40)" if scale == 40 else ""
                    result += f"- {display_university}: {score} điểm{scale_text}\n"

                # Nếu có ít nhất 2 trường và thang điểm đồng nhất, tính chênh lệch
                if len(subset) >= 2 and len(set(scales)) == 1:
                    row1 = subset.iloc[0]
                    row2 = subset.iloc[1]
                    score1 = row1['Điểm Chuẩn']
                    score2 = row2['Điểm Chuẩn']
                    uni_cleaned1 = clean_text(row1['Tên trường'].lower())
                    uni_cleaned2 = clean_text(row2['Tên trường'].lower())
                    major_cleaned = clean_text(row1['Tên Ngành'].lower())
                    method_cleaned = row1['Phương Thức Xét Tuyển'].lower()

                    school1 = row1['Tên trường']
                    school2 = row2['Tên trường']
                    if (uni_cleaned1, major_cleaned, method_cleaned) in name_mapping:
                        school1 = name_mapping[(uni_cleaned1, major_cleaned, method_cleaned)]['Tên trường']
                    if (uni_cleaned2, major_cleaned, method_cleaned) in name_mapping:
                        school2 = name_mapping[(uni_cleaned2, major_cleaned, method_cleaned)]['Tên trường']

                    diff = abs(score1 - score2)
                    higher_school = school1 if score1 > score2 else school2
                    result += f"=> Chênh lệch giữa hai trường là {diff:.2f} điểm, {higher_school} cao hơn.\n"
                elif len(subset) >= 2 and len(set(scales)) > 1:
                    scale_warning = True

    if scale_warning and not compare_quota:
        result += "Một số ngành/trường có thang điểm khác nhau (30 và 40), nên mình chỉ so sánh được các ngành có cùng thang điểm thôi nhé!\n"

    # Thêm thông báo về dữ liệu thiếu (nếu có)
    if missing_data_info:
        result += "\n".join(missing_data_info) + "\n"

    return result

def analyze_trend(df, university, major, years):
    # Kiểm tra thông tin đầu vào
    if not university or len(university) != 1:
        return 'Mình cần thêm thông tin về trường để phân tích xu hướng điểm chuẩn. Bạn có thể cung cấp thêm không?'
    if not major or len(major) != 1:
        return 'Mình cần thêm thông tin về ngành để phân tích xu hướng điểm chuẩn. Bạn có thể cung cấp thêm không?'
    university = university[0]
    major = major[0]

    # Kiểm tra years
    if years is None or years == 'all':
        return 'Mình cần thêm thông tin về năm để phân tích xu hướng điểm chuẩn. Bạn có thể cung cấp thêm không?'

    # Xác định danh sách năm
    try:
        if '-' in years:
            start, end = map(int, years.split('-'))
            years_list = list(range(start, end + 1))
        elif ',' in years:
            years_list = [int(y) for y in years.split(',')]
        else:
            years_list = [int(years)]
    except (ValueError, TypeError):
        return 'Thông tin về năm không hợp lệ. Bạn có thể cung cấp lại thông tin về năm (ví dụ: "2020-2024" hoặc "2020,2022,2024") không?'

    # Kiểm tra số lượng năm
    if len(years_list) < 2:
        return 'Để phân tích xu hướng, mình cần thông tin điểm chuẩn của ít nhất 2 năm. Bạn có thể cung cấp thêm thông tin về năm không?'

    # Chuẩn hóa university và major để so sánh
    university_cleaned = clean_text(university.lower())  # Loại bỏ nội dung trong ngoặc và chuyển thành chữ thường
    major_cleaned = clean_text(major.lower())

    # Chuẩn hóa cột Tên trường và Tên Ngành trong DataFrame
    df['Tên trường_cleaned'] = df['Tên trường'].str.lower().apply(clean_text)
    df['Tên Ngành_cleaned'] = df['Tên Ngành'].str.lower().apply(clean_text)

    # Lọc dữ liệu theo trường, ngành và năm
    df_subset = df[
        (df['Tên trường_cleaned'] == university_cleaned) &
        (df['Tên Ngành_cleaned'] == major_cleaned) &
        (df['Năm'].isin(years_list))
    ]

    # Nếu không tìm thấy dữ liệu, thử fuzzy matching
    if df_subset.empty:
        # Fuzzy matching cho trường
        df['university_match'] = df['Tên trường_cleaned'].apply(lambda x: fuzz.ratio(x, university_cleaned) >= 80)
        # Fuzzy matching cho ngành
        df['major_match'] = df['Tên Ngành_cleaned'].apply(lambda x: fuzz.ratio(x, major_cleaned) >= 80)
        # Lọc lại
        df_subset = df[
            (df['university_match']) &
            (df['major_match']) &
            (df['Năm'].isin(years_list))
        ]

    # Xóa các cột tạm
    df.drop(columns=['Tên trường_cleaned', 'Tên Ngành_cleaned'], inplace=True, errors='ignore')
    df.drop(columns=['university_match', 'major_match'], inplace=True, errors='ignore')

    # Kiểm tra nếu không tìm thấy dữ liệu
    if df_subset.empty:
        return f'Không tìm thấy dữ liệu cho ngành {major} tại trường {university} trong các năm {", ".join(map(str, years_list))}. Bạn có thể kiểm tra lại thông tin hoặc cung cấp thêm dữ liệu không?'

    # Lấy điểm chuẩn theo năm và sắp xếp
    trend = df_subset.groupby('Năm')['Điểm Chuẩn'].first().sort_index()
    if len(trend) < 2:
        return f'Chỉ tìm thấy dữ liệu cho năm {trend.index[0]} (điểm chuẩn: {trend.iloc[0]}). Để phân tích xu hướng, mình cần thông tin điểm chuẩn của ít nhất 2 năm. Bạn có thể cung cấp thêm thông tin về năm không?'

    # Xây dựng chuỗi kết quả
    result = f'Điểm chuẩn ngành {major} tại trường {university} qua các năm:\n'
    scale_40 = False
    for year, score in trend.items():
        scale_text = " (thang điểm 40)" if 31 <= score <= 40 else ""
        if 31 <= score <= 40:
            scale_40 = True
        result += f'- Năm {year}: {score}{scale_text}\n'

    # Phân tích xu hướng và gộp vào một dòng
    diffs = trend.diff().dropna()
    avg_change = diffs.mean()
    result += '\nNhìn chung, điểm chuẩn '
    if avg_change > 0:
        if avg_change > 1.5:
            result += f'tăng khá mạnh, trung bình {avg_change:.2f} điểm mỗi năm, cho thấy xu hướng tăng đáng kể qua các năm.'
        else:
            result += f'tăng nhẹ, trung bình {avg_change:.2f} điểm mỗi năm, cho thấy xu hướng tăng nhưng vẫn khá ổn định qua các năm.'
    elif avg_change < 0:
        if avg_change < -1.5:
            result += f'giảm khá mạnh, trung bình {avg_change:.2f} điểm mỗi năm, cho thấy xu hướng giảm đáng kể qua các năm.'
        else:
            result += f'giảm nhẹ, trung bình {avg_change:.2f} điểm mỗi năm, cho thấy xu hướng giảm nhưng vẫn khá ổn định qua các năm.'
    else:
        result += 'không thay đổi đáng kể, trung bình dao động 0 điểm mỗi năm, cho thấy xu hướng ổn định qua các năm.'

    # Thêm cảnh báo nếu có thang điểm 40
    if scale_40:
        result += '\nLưu ý: Một số năm có điểm chuẩn trong thang điểm 40, bạn nên kiểm tra kỹ phương thức xét tuyển.'

    return result

function_mapping = {
    'extract': gemini_extract,
    'search_action': search_action,
    'do_nothing': do_nothing,
    'answer_question': answer_question,
    'analyze_trend': analyze_trend,
    'filter_by_score': filter_by_score,
    'filter_by_year': filter_by_year,
    'check_pass_chance': check_pass_chance,
    'compare': compare_advanced,
}

def reasoning_step(state, user_input, intermediate_results):
    # Kiểm tra xem info đã tồn tại trong state chưa
    if 'info' not in state:
        # Nếu chưa có, gọi gemini_extract và lưu vào state
        info = gemini_extract(user_input)
        state['info'] = info
    else:
        # Nếu đã có, tái sử dụng info từ state
        info = state['info']

    question_type = info.get('question_type', 'search')
    missing_info = info.get('missing_info', None)

    # Kiểm tra câu hỏi mơ hồ
    if question_type == 'ambiguous':
        return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': missing_info, 'info': info}}

    # Kiểm tra câu hỏi thuộc loại RAG
    if question_type == 'RAG':
        # Gọi hàm rag và trả về kết quả trực tiếp dưới dạng string
        rag_result = rag(user_input)
        return rag_result

    # Kiểm tra thông tin bắt buộc cho câu hỏi loại 'search'
    #if question_type == 'search':  # Chỉ áp dụng cho 'search', không áp dụng cho 'condition_search'
        #university = info.get('university', None)
        #major = info.get('major', None)
        #if (university is None or university == 'all') and (major is None or major == 'all'):
         #   return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': "Mình không thể tìm kiếm vì thiếu thông tin về trường và ngành. Bạn có thể cung cấp thêm thông tin về trường hoặc ngành để mình hỗ trợ không?", 'info': info}}
        #elif university is None or university == 'all':
         #   return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': "Mình không thể tìm kiếm vì thiếu thông tin về trường. Bạn có thể cung cấp thêm tên trường để mình hỗ trợ không?", 'info': info}}
        #elif major is None or major == 'all':
         #   return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': "Mình không thể tìm kiếm vì thiếu thông tin về ngành. Bạn có thể cung cấp thêm tên ngành để mình hỗ trợ không?", 'info': info}}

    # Kiểm tra thông tin bắt buộc cho câu hỏi loại 'compare'
    if question_type == 'compare':
        university = info.get('university', None)
        major = info.get('major', None)
        university_count = len(university) if university and university != 'all' else 0
        major_count = len(major) if major else 0
        # Chỉ yêu cầu bổ sung thông tin nếu không đủ điều kiện so sánh
        if university_count < 2 and major_count < 2:
            missing_info = "Mình cần thêm thông tin để so sánh. "
            if university_count == 0:
                missing_info += "Bạn cần cung cấp ít nhất 2 trường để so sánh nếu không có ngành để so sánh. "
            if major_count == 0:
                missing_info += "Bạn cần cung cấp ít nhất 2 ngành để so sánh nếu chỉ có 1 trường. "
            return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': missing_info, 'info': info}}

    # Nếu không có dữ liệu trung gian, gọi search_action và truyền info
    if not intermediate_results:
        return {'action': 'search_action', 'parameters': {'query': user_input, 'info': info}}

    # Lấy kết quả từ search_action
    search_result = intermediate_results[-1]['result']
    df = search_result['filtered_df']
    original_df = search_result['original_df']

    # Kiểm tra dữ liệu thiếu (cho câu hỏi compare hoặc các câu hỏi liên quan đến quota, combinations)
    missing_data_info = ""
    if question_type in ['compare', 'search', 'condition_search']:
        # Lấy danh sách trường, ngành, phương thức, tổ hợp yêu cầu từ info, mặc định là [] nếu None
        requested_universities = info.get('university', []) or []
        requested_majors = info.get('major', []) if info.get('major') and info['major'] != 'all' else []  # Không tách 'all'
        requested_methods = info.get('method', 'all') if info.get('method') else ['THPT Quốc gia']
        requested_combinations = info.get('combinations', []) or []

        # Lấy danh sách trường, ngành, phương thức, tổ hợp có trong DataFrame đã lọc (df_filtered)
        found_universities = df['Tên trường'].str.lower().apply(clean_text).unique().tolist() if not df.empty else []
        found_majors = df['Tên Ngành'].str.lower().apply(clean_text).unique().tolist() if not df.empty else []
        found_methods = df['Phương Thức Xét Tuyển'].str.lower().unique().tolist() if not df.empty else []
        found_combinations = []
        if 'Tổ hợp' in df.columns:
            # Lấy tất cả tổ hợp có trong DataFrame
            all_combinations = df['Tổ hợp'].dropna().str.split(',').explode().str.strip().str.upper().unique().tolist()
            found_combinations = all_combinations

        # Chuẩn hóa danh sách yêu cầu
        requested_universities_cleaned = [clean_text(u.lower()) for u in requested_universities]
        requested_majors_cleaned = [clean_text(m.lower()) for m in requested_majors] if requested_majors else []
        requested_methods_cleaned = [m.lower() for m in requested_methods] if requested_methods != 'all' else None
        requested_combinations_cleaned = [c.upper().strip() for c in requested_combinations]

        # Kiểm tra trường, ngành, phương thức, tổ hợp thiếu bằng fuzzy matching
        missing_universities = []
        for u in requested_universities:
            u_cleaned = clean_text(u.lower())
            matched = False
            for found_u in found_universities:
                if fuzz.ratio(u_cleaned, found_u) >= 80:  # Sử dụng fuzzy matching với ngưỡng 80
                    matched = True
                    break
            if not matched:
                missing_universities.append(u)

        missing_majors = []
        if info.get('major') != 'all':  # Chỉ kiểm tra nếu major không phải 'all'
            for m in requested_majors:
                m_cleaned = clean_text(m.lower())
                matched = False
                for found_m in found_majors:
                    if fuzz.ratio(m_cleaned, found_m) >= 80:
                        matched = True
                        break
                if not matched:
                    missing_majors.append(m)
        else:
            # Nếu major là 'all', kiểm tra xem có ngành nào không
            if not found_majors:
                missing_majors.append("ngành (không tìm thấy ngành nào)")

        missing_methods = [m for m in requested_methods if m.lower() not in found_methods] if requested_methods != 'all' else []
        missing_combinations = [c for c in requested_combinations_cleaned if c not in found_combinations]

        # Tạo thông báo về dữ liệu thiếu
        missing_parts = []
        if missing_universities:
            missing_parts.append(f"trường {', '.join(missing_universities)}")
        if missing_majors:
            missing_parts.append(f"{', '.join(missing_majors)}")
        if missing_methods:
            missing_parts.append(f"phương thức {', '.join(missing_methods)}")
        if missing_combinations:
            missing_parts.append(f"tổ hợp {', '.join(missing_combinations)}")

        if missing_parts:
            missing_data_info = f"Mình không tìm thấy thông tin về {', '.join(missing_parts)} trong dữ liệu. Mình sẽ trả lời dựa trên những thông tin còn lại nhé!"

        # Lưu thông tin thiếu vào info để answer_question sử dụng
        info['missing_data_info'] = missing_data_info

    # Xử lý dựa trên question_type
    if question_type in ['search', 'condition_search', 'highest_score', 'top_n']:
        # Đã xử lý trong search_action, chỉ cần trả lời
        return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': df, 'info': info}}
    elif question_type == 'compare':
        # Kiểm tra độ phức tạp dựa trên số lượng trường, ngành, phương thức
        num_universities = len(info.get('university', []))
        num_majors = len(info.get('major', []))
        num_methods = len(info.get('method', [])) if info.get('method') and info.get('method') != 'all' else 1
        total_combinations = num_universities * num_majors * num_methods

        # Nếu quá phức tạp (ví dụ: > 4 tổ hợp), gọi compare_advanced
        if total_combinations > 4:
            result = compare_advanced(
                {'filtered_df': df, 'original_df': original_df},
                info.get('university'),
                info.get('major'),
                info.get('year'),
                info.get('method'),
                original_df,
                question=user_input
            )
            return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': result, 'info': info}}
        else:
            # Nếu đơn giản, để API tự xử lý từ DataFrame
            return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': df, 'info': info}}
    elif question_type == 'trend_analysis':
        result = analyze_trend(df, info.get('university'), info.get('major'), info.get('year'))
        return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': result, 'info': info}}
    elif question_type == 'pass_chance':
        user_score = info.get('score')
        if user_score is None:
            return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': "Không tìm thấy điểm thi trong câu hỏi, vui lòng cung cấp điểm thi của bạn!", 'info': info}}
        result = check_pass_chance({'filtered_df': df, 'original_df': original_df}, user_score, info.get('university'), info.get('major'), info.get('year'), info.get('method'), original_df)
        return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': result, 'info': info}}
    else:
        # Nếu không xác định, để LLM xử lý
        return {'action': 'answer_question', 'parameters': {'question': user_input, 'search_results': df, 'info': info}}

def process_tool_calls(response):
    if 'action' not in response:
        return 'do_nothing', {}
    return response['action'], response['parameters']

def agent(user_input):
    state = {'status': 'start', 'history': []}
    intermediate_results = []

    while True:
        action_response = reasoning_step(state, user_input, intermediate_results)
        print('Action Response:', action_response)

        if isinstance(action_response, str):
            return action_response

        tool_function_name, tool_query_string = process_tool_calls(action_response)

        if tool_function_name == 'do_nothing':
            return intermediate_results[-1]['result']

        function_to_call = function_mapping[tool_function_name]
        action_result = function_to_call(**tool_query_string)

        intermediate_results.append({
            'action': tool_function_name,
            'parameters': tool_query_string,
            'result': action_result
        })

        state.update({
            'status': 'in_progress',
            'last_action': tool_function_name,
            'last_parameters': tool_query_string
        })

        if tool_function_name == 'answer_question':
            intermediate_results.append({
                'action': 'do_nothing',
                'parameters': {},
                'result': action_result
            })
            return action_result

def main(user_input):
    result = answer(user_input)
    result_dict = json.loads(result)

    initial_response = result_dict.get("response")
    question_type = result_dict.get("question_type")
    query = result_dict.get("query")

    print('question_type:', question_type)
    print('query:', query)
    # print("🧪 Initial response:", initial_response)
    search_response = None
    if question_type == 'search':
        search_response = agent(query)
        #write_to_db(user_input, search_response)
        return search_response, query
    #write_to_db(user_input, initial_response)
    return initial_response, query
# while True:
#     query = input('enter your question: ')
#     print(main(query))

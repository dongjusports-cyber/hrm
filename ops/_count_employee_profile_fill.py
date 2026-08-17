"""In coverage hồ sơ NV — chạy trong container api."""
from app.core.database import SessionLocal
from app.modules.mdm.models import Employee

db = SessionLocal()
q = db.query(Employee).filter(Employee.deleted_at.is_(None))
n = q.count()


def nz(col) -> int:
    return q.filter(col.isnot(None)).count()


print(f"NV {n}")
print(f"ngay_sinh {nz(Employee.birth_date)}")
print(f"ngay_vao {nz(Employee.join_date)}")
print(f"ky_HD {nz(Employee.contract_signed_at)}")
print(f"luong_HD {q.filter(Employee.contract_salary.isnot(None), Employee.contract_salary > 0).count()}")
print(f"STK {q.filter(Employee.bank_account.isnot(None), Employee.bank_account != '').count()}")
print(f"SDT {q.filter(Employee.phone.isnot(None), Employee.phone != '').count()}")
print(f"CCCD {q.filter(Employee.id_number.isnot(None), Employee.id_number != '').count()}")
print(f"hon_nhan {nz(Employee.marital_status)}")
print(f"co_con {q.filter(Employee.children_count > 0).count()}")
print(f"quoc_tich {q.filter(Employee.nationality_code == 'NATIONALITY001').count()}")
print(f"dan_toc {q.filter(Employee.ethnicity_code == 'ETHNICITY001').count()}")
print(f"ton_giao {q.filter(Employee.religion_code == 'RELIGION001').count()}")
print(f"hoc_van {nz(Employee.education_code)}")
print(f"anh {q.filter(Employee.photo_path.isnot(None), Employee.photo_path != '').count()}")
db.close()

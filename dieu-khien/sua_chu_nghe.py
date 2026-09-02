import unicodedata

TU_NGAN_HANG = (
    "số dư", "tài khoản", "hạn mức", "giao dịch", "chuyển khoản",
    "số điện thoại", "nhân viên",
)
KHOANG_CACH_TOI_DA = 2


def _bo_dau(chu):
    khong_dau = unicodedata.normalize("NFD", chu.lower())
    return "".join(k for k in khong_dau if unicodedata.category(k) != "Mn")


def _khoang_cach(a, b):
    if len(a) < len(b):
        a, b = b, a
    dong_truoc = list(range(len(b) + 1))
    for i, ky_tu_a in enumerate(a, start=1):
        dong = [i]
        for j, ky_tu_b in enumerate(b, start=1):
            dong.append(min(
                dong_truoc[j] + 1,
                dong[j - 1] + 1,
                dong_truoc[j - 1] + (ky_tu_a != ky_tu_b),
            ))
        dong_truoc = dong
    return dong_truoc[-1]


def sua_tu_gan_am(cau):
    cac_tu = cau.split()
    for tu_dung in TU_NGAN_HANG:
        so_tu = len(tu_dung.split())
        for vi_tri in range(len(cac_tu) - so_tu + 1):
            doan = " ".join(cac_tu[vi_tri:vi_tri + so_tu])
            if doan.lower() == tu_dung:
                continue
            if _khoang_cach(_bo_dau(doan), _bo_dau(tu_dung)) <= KHOANG_CACH_TOI_DA:
                cac_tu[vi_tri:vi_tri + so_tu] = tu_dung.split()
                break
    return " ".join(cac_tu)

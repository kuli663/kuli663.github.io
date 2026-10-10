# -*- coding: utf-8 -*-
"""
预演毕业论文配套代码：基于年报文本挖掘的商业银行数字化转型测度
=================================================================
五步流水线（Step1~Step5），纯 Python 标准库实现，无需第三方依赖。

Step1 数据获取      ：构建上市银行年度"年报文本"语料（模拟语料，随机种子固定，完全可复现）
Step2 文本预处理    ：清洗（去标点/空白/数字）、规范化
Step3 测度词典构建  ：加载数字化转型词典（4 个维度），见 data/digital_dictionary.txt
Step4 测度计算      ：关键词词频法计算银行-年度数字化转型指数及各维度得分
Step5 信效度检验    ：描述性统计、Cronbach's α 信度、相关分析、OLS 回归（效度检验）

运行方式：
    python code/pipeline.py
输出：
    data/bank_digital_index_panel.csv   企业-年度面板（测度结果表）
    results/analysis_results.json       描述统计 / 信度 / 相关 / 回归结果
"""

import csv
import json
import math
import os
import random
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

SEED = 20261010  # 全局随机种子，保证结果可复现

# ----------------------------------------------------------------------
# Step 1  数据获取：构建银行-年度年报文本语料（模拟）
# ----------------------------------------------------------------------
BANKS = [
    "工商银行", "建设银行", "农业银行", "中国银行", "交通银行", "招商银行",
    "浦发银行", "民生银行", "兴业银行", "平安银行", "光大银行", "宁波银行",
]
YEARS = list(range(2015, 2025))  # 2015-2024，共 10 年

# 银行层面的数字化禀赋（模拟异质性：招行、平安等转型更快）
BANK_DIGITAL_PROPENSITY = {
    "工商银行": 0.75, "建设银行": 0.72, "农业银行": 0.60, "中国银行": 0.66,
    "交通银行": 0.62, "招商银行": 0.92, "浦发银行": 0.70, "民生银行": 0.64,
    "兴业银行": 0.68, "平安银行": 0.90, "光大银行": 0.65, "宁波银行": 0.80,
}

# 语料模板：数字化语句（含词典关键词占位 {kw}）、中性语句、财务语句
DIGITAL_TEMPLATES = [
    "本行加大{kw}投入，推动业务流程再造与经营模式升级。",
    "报告期内，本行依托{kw}持续提升客户服务体验。",
    "本行将{kw}作为战略重点，全年相关投入同比增长。",
    "围绕{kw}，本行完成多个重点项目建设并投入运营。",
    "本行深化{kw}应用，风险识别与运营效率明显改善。",
    "在{kw}领域，本行与外部机构开展合作，取得积极进展。",
    "管理层高度重视{kw}，将其纳入中长期发展规划。",
    "本行持续推进{kw}落地，相关指标位居同业前列。",
]
NEUTRAL_TEMPLATES = [
    "报告期内，本行坚持稳健经营，各项业务平稳发展。",
    "本行严格遵守监管要求，持续完善公司治理结构。",
    "面对复杂的外部环境，本行保持战略定力。",
    "本行积极履行社会责任，支持实体经济发展。",
    "报告期内，本行资产质量保持稳定，拨备覆盖充足。",
    "本行加强全面风险管理，守住不发生系统性风险底线。",
    "董事会认真履行职责，审议通过了多项重要议案。",
    "本行持续推进网点转型，提升综合服务能力。",
    "本行优化资产负债结构，净息差保持在合理区间。",
    "本行重视人才队伍建设，完善培训与激励机制。",
]
FINANCE_TEMPLATES = [
    "报告期末，本行总资产较上年末增长，盈利能力保持稳定。",
    "本行实现营业收入和净利润双增长，成本收入比下降。",
    "不良贷款率较上年末下降，资产质量进一步夯实。",
    "资本充足率满足监管要求，资本实力持续增强。",
    "中间业务收入占比提升，收入结构不断优化。",
]

PUNCT_RE = re.compile(r"[，。、；：？！“”‘’（）《》〈〉【】—…·\s0-9A-Za-z%]+")


def step1_build_corpus():
    """Step1：为每家银行每一年生成一段'年报文本'，并模拟财务变量。

    数字化语句数量 ~ 与银行禀赋、年份趋势正相关，叠加泊松噪声，
    使'真实'数字化水平与文本中关键词出现次数存在已知关系，便于后续效度检验。
    """
    corpus = {}   # (bank, year) -> raw text
    truth = {}    # (bank, year) -> 真实数字化强度（用于模拟财务变量）
    for bank in BANKS:
        propensity = BANK_DIGITAL_PROPENSITY[bank]
        for year in YEARS:
            rng = random.Random(f"{SEED}-{bank}-{year}")
            trend = (year - YEARS[0]) / (len(YEARS) - 1)          # 0→1 时间趋势
            lam = 3 + 45 * (0.45 * propensity + 0.55 * trend)     # 期望数字化语句数
            n_digital = max(0, int(rng.gauss(lam, 3.5)))
            n_neutral = rng.randint(24, 34)
            n_finance = rng.randint(6, 10)

            sents = []
            kw_pool = [kw for kws in load_dictionary().values() for kw in kws]
            for _ in range(n_digital):
                sents.append(rng.choice(DIGITAL_TEMPLATES).format(kw=rng.choice(kw_pool)))
            for _ in range(n_neutral):
                sents.append(rng.choice(NEUTRAL_TEMPLATES))
            for _ in range(n_finance):
                sents.append(rng.choice(FINANCE_TEMPLATES))
            rng.shuffle(sents)
            corpus[(bank, year)] = "".join(sents)
            truth[(bank, year)] = lam  # 真实强度
    return corpus, truth


# ----------------------------------------------------------------------
# Step 2  文本预处理：清洗与规范化
# ----------------------------------------------------------------------
def step2_preprocess(text):
    """去除标点、空白、数字与英文字母，得到纯净汉字序列。

    词典法的关键词匹配不依赖分词（直接子串匹配），
    因此预处理只需保证文本规范化、无噪声字符。
    """
    cleaned = PUNCT_RE.sub("", text)
    return cleaned


# ----------------------------------------------------------------------
# Step 3  测度词典构建：加载四维数字化转型词典
# ----------------------------------------------------------------------
def load_dictionary():
    """从 data/digital_dictionary.txt 加载词典。

    文件格式：# 维度名 标题行 + 每行一个关键词。
    """
    path = os.path.join(DATA_DIR, "digital_dictionary.txt")
    dictionary, dim = {}, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                dim = line.lstrip("# ").strip()
                dictionary[dim] = []
            else:
                dictionary[dim].append(line)
    return dictionary


# ----------------------------------------------------------------------
# Step 4  测度计算：关键词词频法构建银行-年度数字化转型指数
# ----------------------------------------------------------------------
def step4_measure(cleaned_corpus, dictionary):
    """对每篇清洗后文本统计各维度关键词出现次数，构建指数。

    指数定义（参照吴非等(2021)）：
        DigitalIndex_{i,t} = ln(1 + Σ_d Count_{i,t,d})
    各维度得分：Score_{i,t,d} = Count_{i,t,d} / 词典维度词数（强度调整）
    """
    rows = []
    for (bank, year), text in sorted(cleaned_corpus.items()):
        total_chars = len(text)
        counts, total_hits = {}, 0
        for dim, kws in dictionary.items():
            c = sum(text.count(kw) for kw in kws)
            counts[dim] = c
            total_hits += c
        index = math.log(1 + total_hits)
        row = {
            "bank": bank,
            "year": year,
            "total_chars": total_chars,
            "digital_keyword_hits": total_hits,
            "keyword_per_kchar": round(total_hits / total_chars * 1000, 3),
            "digital_index": round(index, 4),
        }
        for dim, kws in dictionary.items():
            row[f"score_{dim}"] = round(counts[dim] / len(kws), 3)
        rows.append(row)
    return rows


# ----------------------------------------------------------------------
# Step 5  信效度检验：描述统计 / 信度 / 相关 / 回归
# ----------------------------------------------------------------------
def simulate_financials(truth):
    """模拟财务变量：ROA 与真实数字化强度正相关（已知因果结构，用于效度检验）。"""
    fin = {}
    for bank in BANKS:
        base_roa = random.Random(f"{SEED}-roa-{bank}").uniform(0.55, 1.15)
        size = random.Random(f"{SEED}-size-{bank}").uniform(27.5, 30.5)  # ln(总资产)
        for year in YEARS:
            rng = random.Random(f"{SEED}-fin-{bank}-{year}")
            lam = truth[(bank, year)]
            roa = base_roa + 0.012 * lam + rng.gauss(0, 0.06)
            fin[(bank, year)] = {"roa": round(roa, 4), "ln_assets": round(size + rng.gauss(0, 0.05), 3)}
    return fin


def mean(xs):
    return sum(xs) / len(xs)


def variance(xs, ddof=1):
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - ddof)


def pearson(x, y):
    mx, my = mean(x), mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den


def cronbach_alpha(item_matrix):
    """item_matrix: N×k，每列一个维度得分。α = k/(k-1) * (1 - Σσ_j²/σ_total²)"""
    k = len(item_matrix[0])
    cols = [[row[j] for row in item_matrix] for j in range(k)]
    totals = [sum(row) for row in item_matrix]
    return k / (k - 1) * (1 - sum(variance(c) for c in cols) / variance(totals))


def ols(y, X):
    """最小二乘：X 已含截距列。返回 beta、标准误、t 值、R²。"""
    n, p = len(X), len(X[0])
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(p)]
    beta = solve(XtX, Xty)
    resid = [y[i] - sum(X[i][a] * beta[a] for a in range(p)) for i in range(n)]
    sigma2 = sum(r ** 2 for r in resid) / (n - p)
    XtX_inv = inverse(XtX)
    se = [math.sqrt(sigma2 * XtX_inv[a][a]) for a in range(p)]
    tvals = [beta[a] / se[a] for a in range(p)]
    sst = sum((v - mean(y)) ** 2 for v in y)
    r2 = 1 - sum(r ** 2 for r in resid) / sst
    return beta, se, tvals, r2


def solve(A, b):
    """高斯消元解线性方程组。"""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            M[r] = [x - f * y for x, y in zip(M[r], M[col])]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))) / M[r][r]
    return x


def inverse(A):
    n = len(A)
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        d = M[col][col]
        M[col] = [x / d for x in M[col]]
        for r in range(n):
            if r != col:
                f = M[r][col]
                M[r] = [x - f * y for x, y in zip(M[r], M[col])]
    return [row[n:] for row in M]


def step5_validate(rows, dictionary, fin):
    dims = list(dictionary.keys())
    index = [r["digital_index"] for r in rows]
    roa = [fin[(r["bank"], r["year"])]["roa"] for r in rows]
    size = [fin[(r["bank"], r["year"])]["ln_assets"] for r in rows]

    # 描述性统计
    desc = {}
    for name, xs in [("digital_index", index), ("roa", roa), ("ln_assets", size)] + \
                    [(f"score_{d}", [r[f"score_{d}"] for r in rows]) for d in dims]:
        desc[name] = {"mean": round(mean(xs), 4), "std": round(math.sqrt(variance(xs)), 4),
                      "min": round(min(xs), 4), "max": round(max(xs), 4), "n": len(xs)}

    # 信度：四维得分 Cronbach's α
    item_matrix = [[r[f"score_{d}"] for d in dims] for r in rows]
    alpha = cronbach_alpha(item_matrix)

    # 效度：指数与 ROA 相关；逐年趋势
    corr_roa = pearson(index, roa)
    year_mean = {y: round(mean([r["digital_index"] for r in rows if r["year"] == y]), 4) for y in YEARS}

    # OLS：roa = β0 + β1·digital_index + β2·ln_assets + ε
    X = [[1.0, index[i], size[i]] for i in range(len(rows))]
    beta, se, tvals, r2 = ols(roa, X)
    reg = {"dep_var": "roa",
           "coef": {"const": round(beta[0], 4), "digital_index": round(beta[1], 4),
                    "ln_assets": round(beta[2], 4)},
           "se": {"const": round(se[0], 4), "digital_index": round(se[1], 4),
                  "ln_assets": round(se[2], 4)},
           "t": {"const": round(tvals[0], 3), "digital_index": round(tvals[1], 3),
                 "ln_assets": round(tvals[2], 3)},
           "r2": round(r2, 4), "n": len(rows)}

    return {"descriptives": desc, "cronbach_alpha": round(alpha, 4),
            "corr_index_roa": round(corr_roa, 4), "yearly_mean_index": year_mean,
            "regression": reg}


# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------
def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 60)
    print("Step 1  数据获取：构建银行-年度年报文本语料（模拟，种子固定）")
    corpus, truth = step1_build_corpus()
    print(f"  语料规模：{len(BANKS)} 家银行 × {len(YEARS)} 年 = {len(corpus)} 篇文本")

    print("Step 2  文本预处理：清洗标点/空白/数字/字母")
    cleaned = {k: step2_preprocess(v) for k, v in corpus.items()}
    sample_len = [len(v) for v in cleaned.values()]
    print(f"  清洗后文本长度：均值 {mean(sample_len):.0f} 字（{min(sample_len)}~{max(sample_len)}）")

    print("Step 3  测度词典构建：加载数字化转型词典")
    dictionary = load_dictionary()
    for dim, kws in dictionary.items():
        print(f"  维度[{dim}]：{len(kws)} 个关键词")

    print("Step 4  测度计算：关键词词频法构建数字化转型指数")
    rows = step4_measure(cleaned, dictionary)
    fin = simulate_financials(truth)
    for r in rows:
        r.update(fin[(r["bank"], r["year"])])
    panel_path = os.path.join(DATA_DIR, "bank_digital_index_panel.csv")
    with open(panel_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  面板数据已写入：{panel_path}（{len(rows)} 行）")

    print("Step 5  信效度检验与回归分析")
    results = step5_validate(rows, dictionary, fin)
    res_path = os.path.join(RESULTS_DIR, "analysis_results.json")
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Cronbach's α = {results['cronbach_alpha']}")
    print(f"  指数与ROA相关系数 r = {results['corr_index_roa']}")
    reg = results["regression"]
    print(f"  OLS：roa = {reg['coef']['const']} + {reg['coef']['digital_index']}·Index "
          f"+ {reg['coef']['ln_assets']}·lnAssets，R² = {reg['r2']}")
    print(f"  结果已写入：{res_path}")
    print("=" * 60)
    print("五步流水线运行完毕，全部结果可复现（种子 SEED = %d）" % SEED)


if __name__ == "__main__":
    main()

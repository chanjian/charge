from django.shortcuts import render
from web.models import QbSearch

def qbsearch(request):
    target_qb = request.GET.get("qb")
    if target_qb is not None:
        try:
            target_qb = int(target_qb)
            if target_qb == 0:
                target_qb = None
        except ValueError:
            target_qb = None
    else:
        target_qb = None

    if target_qb is not None:
        # 完全命中查询，确保 exact_matches 是一个查询集
        exact_matches = QbSearch.objects.filter(qb=target_qb)
        if exact_matches.exists():
            results = [{
                "qb": match.qb,
                "combo": match.combo,
                "points": match.points,
                "calculation": match.calculation
            } for match in exact_matches]
            return render(request, "qbsearch.html", {"status": "exact", "results": results, "target_qb": target_qb})

        # 左边界查询（小于等于目标的最大值）
        left_matches = QbSearch.objects.filter(qb__lte=target_qb).order_by("-qb").first()

        # 右边界查询（大于等于目标的最小值）
        right_matches = QbSearch.objects.filter(qb__gte=target_qb).order_by("qb").first()

        # 格式化左边界结果
        if left_matches:
            left_qb = left_matches.qb
            left_results = QbSearch.objects.filter(qb=left_qb)
        else:
            left_results = []

        # 格式化右边界结果
        if right_matches:
            right_qb = right_matches.qb
            right_results = QbSearch.objects.filter(qb=right_qb)
        else:
            right_results = []

        # 格式化结果
        results = {}
        if left_results:
            results["left"] = [{
                "qb": match.qb,
                "combo": match.combo,
                "points": match.points,
                "calculation": match.calculation
            } for match in left_results]

        if right_results:
            results["right"] = [{
                "qb": match.qb,
                "combo": match.combo,
                "points": match.points,
                "calculation": match.calculation
            } for match in right_results]

        context = {
            "status": "boundary",
            "results": results,
            "target_qb": target_qb,
        }

        return render(request, "qbsearch.html", context)
    else:
        # 如果 target_qb 为 None，直接返回一个包含提示信息的页面
        context = {
            "status": None,
            "results": {},
            "target_qb": None,
        }
        return render(request, "qbsearch.html", context)
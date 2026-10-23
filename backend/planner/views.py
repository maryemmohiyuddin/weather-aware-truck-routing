from rest_framework.response import Response
from rest_framework.views import APIView

from planner.services.errors import UpstreamError
from planner.services.geocode import search_places
from planner.services.plan import build_plan
from planner.validate import ValidationError, parse_plan_request


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class GeocodeView(APIView):
    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return Response({"results": []})
        if len(query) > 200:
            return Response({"error": "Search text is too long."}, status=400)
        try:
            results = search_places(query)
        except UpstreamError as exc:
            return Response({"error": str(exc)}, status=502)
        return Response({"results": results})


class PlanView(APIView):
    def post(self, request):
        try:
            plan_request = parse_plan_request(request.data)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=400)
        try:
            plan = build_plan(plan_request)
        except UpstreamError as exc:
            return Response({"error": str(exc)}, status=502)
        return Response(plan)

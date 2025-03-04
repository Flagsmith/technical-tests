from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
def get_flags(request: Request) -> Response:
    # TODO: Implement this view as per requirements in Readme.md
    return Response()

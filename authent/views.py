from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
import jwt
from .utils import create_jwt_for_user, decode_jwt, get_user_from_token, token_required
import json

User = get_user_model()


@require_POST
def register_view(request):
    """Register a new user.
    Expected JSON body: {"username": "...", "email": "...", "password": "..."}
    Returns: {"token": "<jwt>", "user": {"id":..., "username":..., "email":...}}
    """
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not password:
        return JsonResponse({"detail": "username and password required"}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"detail": "username already taken"}, status=400)

    if email and User.objects.filter(email=email).exists():
        return JsonResponse({"detail": "email already taken"}, status=400)

    user = User.objects.create(
        username=username,
        email=email or "",
        password=make_password(password),
    )

    token = create_jwt_for_user(user)
    return JsonResponse(
        {
            "token": token,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        },
        status=201,
    )


@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

    password = data.get("password")
    username = data.get("username")
    email = data.get("email")

    if not password:
        return JsonResponse({"detail": "password required"}, status=400)

    user = None
    if username:
        user = authenticate(request, username=username, password=password)
    elif email:
        try:
            u = User.objects.get(email=email)
        except User.DoesNotExist:
            u = None
        if u and u.check_password(password):
            user = u

    if user is None:
        return JsonResponse({"detail": "invalid credentials"}, status=401)

    token = create_jwt_for_user(user)
    return JsonResponse(
        {
            "token": token,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }
    )


@require_POST
def verify_token_view(request):
    """Verify a token. Accepts either JSON {"token": "..."} or Authorization header Bearer <token>.
    Returns token payload and user summary on success.
    """
    # Try header first
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    token = None
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1].strip()
    else:
        try:
            data = json.loads(request.body)
            token = data.get("token")
        except Exception:
            token = None

    if not token:
        return JsonResponse({"detail": "No token provided"}, status=400)

    try:
        payload = decode_jwt(token)
    except jwt.ExpiredSignatureError:
        return JsonResponse({"detail": "token expired"}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({"detail": "invalid token"}, status=401)

    user = get_user_from_token(token)
    if user is None:
        return JsonResponse({"detail": "user not found"}, status=401)

    return JsonResponse(
        {
            "payload": payload,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }
    )


@require_GET
@token_required
def me_view(request):
    """Protected endpoint that returns current user's info.
    Access with Authorization: Bearer <token>
    """
    user = request.user
    return JsonResponse({"id": user.id, "username": user.username, "email": user.email})

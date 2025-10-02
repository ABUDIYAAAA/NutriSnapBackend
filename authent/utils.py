from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
import jwt
from datetime import datetime, timedelta

User = get_user_model()


JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 60 * 60 * 24 * 30


def create_jwt_for_user(user):
    """Return encoded JWT for a user."""
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_jwt(token):
    """Decode JWT and return payload or raise jwt exceptions."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    return payload


def get_user_from_token(token):
    payload = decode_jwt(token)
    user_id = payload.get("user_id")
    if not user_id:
        return None
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def token_required(view_func):
    """A decorator that expects Authorization: Bearer <token> header.
    If valid, attaches request.user (not using Django session) and calls view_func.
    Otherwise returns JsonResponse with 401.
    """

    def _wrapped(request, *args, **kwargs):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer "):
            return JsonResponse(
                {"detail": "Authorization header missing or invalid"}, status=401
            )
        token = auth.split(" ", 1)[1].strip()
        try:
            user = get_user_from_token(token)
        except jwt.ExpiredSignatureError:
            return JsonResponse({"detail": "Token has expired"}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({"detail": "Invalid token"}, status=401)

        if user is None:
            return JsonResponse({"detail": "User not found"}, status=401)

        request.auth_token = token
        return view_func(request, *args, **kwargs)

    return _wrapped

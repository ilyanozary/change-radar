from fastapi import Depends as Need
from tokens import validate_token as verify


def principal(token=Need(verify)):
    return token

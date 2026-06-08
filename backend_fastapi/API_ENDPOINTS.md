# Sprint 1 Implementation - API Endpoints Overview

## Authentication Endpoints

POST /api/v1/auth/register
- Create new user account
- Request: {name, email, password, role}
- Response: {access_token, refresh_token, token_type}
- Status: 201 Created

POST /api/v1/auth/login
- Authenticate user
- Request: {email, password}
- Response: {access_token, refresh_token, token_type}
- Status: 200 OK

POST /api/v1/auth/refresh
- Refresh access token
- Request: {refresh_token}
- Response: {access_token, refresh_token, token_type}
- Status: 200 OK

GET /api/v1/auth/me
- Get current authenticated user
- Header: Authorization: Bearer {token}
- Response: {id, name, email, role}
- Status: 200 OK

## Users Endpoints

GET /api/v1/users
- List all users
- Response: [{id, name, email, role, created_at, updated_at}, ...]
- Status: 200 OK

GET /api/v1/users/{user_id}
- Get user details
- Response: {id, name, email, role, created_at, updated_at}
- Status: 200 OK

## Clubs Endpoints

POST /api/v1/clubs
- Create club
- Request: {name, city?}
- Response: {id, name, city, created_at}
- Status: 201 Created

GET /api/v1/clubs
- List all clubs
- Response: [{id, name, city, created_at}, ...]
- Status: 200 OK

GET /api/v1/clubs/{club_id}
- Get club details
- Response: {id, name, city, created_at}
- Status: 200 OK

## Coaches Endpoints

POST /api/v1/coaches
- Create coach
- Request: {user_id, club_id?}
- Response: {id, user_id, club_id, created_at}
- Status: 201 Created

GET /api/v1/coaches/{coach_id}
- Get coach details
- Response: {id, user_id, club_id, created_at}
- Status: 200 OK

## Goalkeepers Endpoints

POST /api/v1/goalkeepers
- Create goalkeeper
- Request: {club_id, name, birth_date?, dominant_hand?, height_cm?, weight_kg?}
- Response: {id, club_id, name, birth_date, dominant_hand, height_cm, weight_kg, created_at}
- Status: 201 Created

GET /api/v1/goalkeepers
- List goalkeepers (optionally filter by club_id)
- Query params: club_id?
- Response: [{id, club_id, name, ...}, ...]
- Status: 200 OK

GET /api/v1/goalkeepers/{gk_id}
- Get goalkeeper details
- Response: {id, club_id, name, birth_date, dominant_hand, height_cm, weight_kg, created_at}
- Status: 200 OK

## Health & Info Endpoints

GET /health
- Health check
- Response: {status: "ok", service: "Goalkeeper AI API"}
- Status: 200 OK

GET /
- Service info
- Response: {name, version, docs}
- Status: 200 OK

## OpenAPI Documentation

GET /docs
- Interactive Swagger UI for all endpoints

GET /openapi.json
- OpenAPI schema in JSON format

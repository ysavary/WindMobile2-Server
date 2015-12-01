curl -X POST -H "Content-Type: application/json" -d '{"username":"yann","password":"123"}' -v http://localhost:8000/api/2/auth/login/

curl -X POST -H "Content-Type: application/json" -H "Authorization: JWT xxx.yyy.zzz" -d '{"station_id": "jdc-1001"}' -v http://localhost:8000/api/2/users/profile/favorites/

curl -H "Authorization: JWT xxx.yyy.zzz" -v http://localhost:8000/api/2/users/profile/

# 코레일 KTX 예매 텔레그램 챗봇

> 아... 지금 보니까 전부 다 리펙토링 하고 싶은데 귀찮다....

## 주의사항

1. 귀경길 기차 예매를 하지 못한 안타까운 영혼들을 위해 만든 프로그램이므로, 개인용 목적이 아닌 상업적 목적등으로 이용하는 것을 엄중히 금합니다.
2. 본 프로그램을 사용할 경우, 기본으로 설정된 1초에 1번 조회 요청에 대한 설정 값 이상으로 빠르게 설정하지 마십시오. 코레일 서버에 무리가 갈 뿐 아니라, 단위 시간내에 보다 빠른 값으로 조회를 요청할 경우, 계정이 정지될 수 있습니다.
3. 본 프로그램은 2021-02-07일 기준으로 정상 동작하지만, 사이트의 구성이나 변수명 변경등에 따라 언제든 동작하지 않을 수 있습니다.

## 설정법

### SSL 인증서(fullchain인증서, 개인키) 및 도메인 값 설정

1. 텔레그램 api의 webhook을 수신할 때 설정할 도메인에 해당하는 SSL 인증서를 `/source/certs` 디렉토리에 위치시킨다. 풀체인 인증서와 개인키 파일 두개가 필요하다. 예시에서는 `fullchain.pem`, `privkey.pem`  라는 이름으로 두개의 파일을 설정하였다.
2. `/nginx/wsgi.conf` 에 인증서 파일명을 명시하여 설정을 완료한다.


```config
server {
    listen  8080; //서비스 포트
    server_name ~^.*$

    ssl                  on;
    ssl_certificate      /source/certs/fullchain.pem; //풀체인 인증서파일명
    ssl_certificate_key  /source/certs/privkey.pem;   //개인키 파일명
    ssl_session_timeout  5m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers  "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
    ssl_prefer_server_ciphers   on;

    location /telebot {
            include uwsgi_params;
            uwsgi_pass unix:/source/telebot.sock;
    }
}
```

### 텔레그램 봇 토큰 설정

환경변수로 `BOTTOEKN` 에 토큰 전달

### 도커 build

git 디렉토리의 최 상위 경로에서 위의 설정들(인증서, 토큰)을 모두 완료 한 후 아래 명령을 통해 빌드할 수 있다.

```docker
docker build -t [사용할 이미지명] -f docker/Dockerfile .
```

### 도커 실행

빌드 된 이미지를 실행하려면 아래와 같이 실행할 수 있다.(nginx 설정에서 동작포트틑 바꾸지 않았을 경우 예시)

```bash
docker run -dit -p [외부에 노출시킬 포트]:8080 [빌드한 이미지명]

# 관리자편의 로그인 기능 사용하고 싶은 경우
docker run -dit -e USERID=[본인코레인ID] -e USERPW=[본인코레일PW] -p [외부에 노출시킬 포트]:8080 [빌드한 이미지명]
```

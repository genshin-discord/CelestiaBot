# GenshinBot registration help

## /reg command
![image](https://user-images.githubusercontent.com/109652760/180729149-44a5c0ff-2121-4863-90f6-a935663f3a47.png)

* **Input your cookies** from hoyolab/米游社! NOT your ingame UID!
* Once registered, bot will start working and fetch all your data!
* Sometimes cookies will expire, you must redo /reg again to enbale your account.

## How to get cookies on pc

1. Login [hoyolab](https://www.hoyolab.com/home) or [米游社](https://bbs.mihoyo.com/ys/)
2. Press **F12**
3. input ```document.cookie```
4. Copy that string and paste into bot's /reg command.

![image](https://user-images.githubusercontent.com/109652760/180731069-5519c333-587c-4afa-8fb2-8f54613bca7f.png)

*Note: this cookies string is shorter than normal because I'm not logged in.*

## How to get cookies on mobile phone

1. Open random page with safari, I'm using google as example.
2. Press share button and add this page as bookmark.

![image](https://user-images.githubusercontent.com/109652760/180732219-00b9865e-17bc-463e-a46d-b422ccb33f91.png)

4. Open bookmark manager and find your new bookmark.
5. Edit this bookmark.
6. Change url to ```javascript:prompt('Cookies:'+document.domain,document.cookie)```

![image](https://user-images.githubusercontent.com/109652760/180732716-3a24fd43-6451-43ec-b82a-1594d23c72d2.png)

7. Save bookmark.
8. Navigate to [hoyolab](https://www.hoyolab.com/home) or [米游社](https://bbs.mihoyo.com/ys/) and login
9. After you login, open that bookmark, copy eveything in prompt and paste into bot's /reg command

![image](https://user-images.githubusercontent.com/109652760/180732781-d388e0b6-6a70-40db-941b-a65223c993df.png)

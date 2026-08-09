def base_template(title, body):

    return f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

</head>

<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">

<table width="100%" cellpadding="25">

<tr>

<td align="center">

<table width="650"
style="background:white;border-radius:15px;overflow:hidden;">

<tr>

<td style="
background:#0d6efd;
padding:25px;
color:white;
text-align:center;
">

<h1>

🏠 Room Chha

</h1>

<p>

Nepal's Smart Rental Platform

</p>

</td>

</tr>

<tr>

<td style="padding:35px;">

<h2>{title}</h2>

{body}

</td>

</tr>

<tr>

<td style="
background:#f8f9fa;
text-align:center;
padding:20px;
font-size:13px;
color:#666;
">

© 2026 Room Chha

<br>

Thank you for using Room Chha ❤️

</td>

</tr>

</table>

</td>

</tr>

</table>

</body>

</html>

"""
def room_approved(name, city):

    body=f"""

<p>

Hello <b>{name}</b>,

</p>

<p>

Congratulations!

</p>

<p>

Your room in

<b>{city}</b>

has been approved.

</p>

<p>

You can now receive applications.

</p>

"""

    return base_template(

        "Room Approved 🎉",

        body

    )
def room_rejected(name, city):

    body=f"""

<p>

Hello <b>{name}</b>

</p>

<p>

Unfortunately your room in

<b>{city}</b>

was rejected.

</p>

<p>

Please update the information and submit again.

</p>

"""

    return base_template(

        "Room Rejected",

        body

    )
def wallet_approved(name, amount):

    body=f"""

<p>

Hello <b>{name}</b>

</p>

<p>

Rs. {amount}

has been added to your wallet.

</p>

"""

    return base_template(

        "Wallet Updated 💰",

        body

    )
def wallet_rejected(name):

    body=f"""

<p>

Hello <b>{name}</b>

</p>

<p>

Your wallet deposit request has been rejected.

</p>

"""

    return base_template(

        "Wallet Deposit Rejected",

        body

    )
def welcome_email(name):

    body=f"""

<h3>

Welcome {name} 👋

</h3>

<p>

Thank you for joining Room Chha.

</p>

<p>

We hope you find your perfect room.

</p>

"""

    return base_template(

        "Welcome to Room Chha",

        body

    )
def new_room_notification(room):

    return f"""
    <h2>🏠 New Room Available</h2>

    <p>A new room matching your preferences has been added.</p>

    <hr>

    <b>City:</b> {room.city}<br>

    <b>Area:</b> {room.area}<br>

    <b>Room Type:</b> {room.room_type}<br>

    <b>Rent:</b> Rs. {room.rent}<br>

    <br>

    Visit Room Chha to see full details.

    <br><br>

    Thanks,

    <br>

    <b>Room Chha Team</b>
    """
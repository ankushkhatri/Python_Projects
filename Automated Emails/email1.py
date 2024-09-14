import yagmail

email = yagmail.SMTP(user="ankushkhatri.k@gmail.com", password="xqme tjiv oolc xxdd")
email.send(to='ankushkhatri.k@gmail.com', 
           subject='Hello Boss',
           contents='Kya haal hai?')
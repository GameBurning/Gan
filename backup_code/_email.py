import smtplib

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login("sdi.gbn@gmail.com", "")

msg = "Baobao!"
server.sendmail("sdi.gbn@gmail.com", "boningga@usc.edu", msg)
server.quit()
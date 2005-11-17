import re

Dependencies = []

def execute(macro, args):
    return macro.formatter.rawHTML('<center><form action="https://www.paypal.com/cgi-bin/webscr" method="post"> <input type="hidden" name="cmd" value="_xclick"> <input type="hidden" name="business" value="daviswiki@gmail.com"> <input type="hidden" name="item_name" value="DavisWiki"> <input type="hidden" name="item_number" value="1"> <input type="hidden" name="no_note" value="1"> <input type="hidden" name="currency_code" value="USD"> <input type="hidden" name="tax" value="0"> <input type="image" src="https://www.paypal.com/en_US/i/btn/x-click-but21.gif" border="0" name="submit" alt="Make payments with PayPal - it\'s fast, free and secure!"> </form></center>')

import bingx
import time
import threading as th


def token_thread(object, token, api, secret):
	trader = bingx.Trader(object, token, api, secret)
	analysis = bingx.Analysis(api, secret)

	while object.get_flag_work():
		orders_id, price, volume_in_coin = trader.make_order(1000)
		trader.wait_close_position()
		quantity_trades = 0
		for order in orders_id:
			quantity_trades = trader.cancel_pending_order(order, quantity_trades)
		volume = float("{:.2f}".format(price * volume_in_coin * quantity_trades))
		object.calculation_volume(volume)
		time.sleep(5)
	trader.wait_close_position()
	trader.cancel_all_orders()


if __name__ == '__main__':
	APIKEY = "NfSS5fn6EppDZT5Z4HPxN0XdQ7VQ75oxjPNBjPda0GiMZa1dHzLcymuH9VmhSIxTl5dAtciVgX1WGJzJ4hA"
	SECRETKEY = "80H8hc40JInDpLTPotm6TSCVVMfmWYZKB2hj3HnmcsNRk3LHsS8lq6yjUXgRNgCpJAJqK6gzCyMmDl5Wv1lcg"
	main = bingx.Bingx(APIKEY, SECRETKEY)
	print(main._get_server_time())
	main.set_position_mode()
	tokens = ("XRP-USDT", "SOL-USDT", "ADA-USDT", "XLM-USDT", "DOT-USDT")
	threads = []
	# token_thread(main, "XRP-USDT", APIKEY, SECRETKEY)
	for token in tokens:
		t = th.Thread(target=token_thread, args=(main, token, APIKEY, SECRETKEY))
		t.start()
		threads.append(t)
		time.sleep(5)
	time.sleep(300)
	print(main.get_total_volume())
	main.work_off()

import bingx
import time
import threading as th


def token_thread(object, token, api, secret):
	trader = bingx.Trader(object, token, api, secret)
	analysis = bingx.Analysis(api, secret)
	print(analysis.get_funding_rate(token))

	while object.get_flag_work():
		orders_id = trader.make_order(1000)
		trader.wait_close_position()
		for order in orders_id:
			trader.cancel_pending_order(order)
		time.sleep(5)
	trader.wait_close_position()
	trader.cancel_all_orders()


def calculation_trading_cost_and_volume(object, api, secret, last_time_check):
	analysis = bingx.Analysis(api, secret)
	# print(analysis.get_funding_rate())
	while object.get_flag_work():
		cost, volume, last_time_check = analysis.get_trading_cost_and_volume(last_time_check)
		object.calculation_cost(cost)
		object.calculation_volume(volume)
		print('ОБЪЕМ', object.get_total_volume())
		print('СТОИМОСТЬ', object.get_total_pnl())
		time.sleep(60)


if __name__ == '__main__':
	APIKEY = "NfSS5fn6EppDZT5Z4HPxN0XdQ7VQ75oxjPNBjPda0GiMZa1dHzLcymuH9VmhSIxTl5dAtciVgX1WGJzJ4hA"
	SECRETKEY = "80H8hc40JInDpLTPotm6TSCVVMfmWYZKB2hj3HnmcsNRk3LHsS8lq6yjUXgRNgCpJAJqK6gzCyMmDl5Wv1lcg"
	tokens = ("XRP-USDT", "SOL-USDT", "ADA-USDT", "XLM-USDT", "DOT-USDT")

	main = bingx.Bingx(APIKEY, SECRETKEY)
	start_time = main.get_server_time()
	print(start_time)
	main.set_position_mode()
	token_thread(main, 'XRP-USDT', APIKEY, SECRETKEY)
	# for token in tokens:
	# 	th.Thread(target=token_thread, args=(main, token, APIKEY, SECRETKEY)).start()
	# 	time.sleep(5)
	th.Thread(target=calculation_trading_cost_and_volume, args=(main, APIKEY, SECRETKEY, start_time)).start()

	# time.sleep(300)
	# print('ОБЪЕМ', main.get_total_volume())
	# print('СТОИМОСТЬ', main.get_total_cost())
	# main.work_off()

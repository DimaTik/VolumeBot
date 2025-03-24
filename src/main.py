import bingx
import time


def main():
	APIKEY = "NfSS5fn6EppDZT5Z4HPxN0XdQ7VQ75oxjPNBjPda0GiMZa1dHzLcymuH9VmhSIxTl5dAtciVgX1WGJzJ4hA"
	SECRETKEY = "80H8hc40JInDpLTPotm6TSCVVMfmWYZKB2hj3HnmcsNRk3LHsS8lq6yjUXgRNgCpJAJqK6gzCyMmDl5Wv1lcg"
	token = 'ADA-USDT'
	trader = bingx.Trader(token, APIKEY, SECRETKEY)
	analysis = bingx.Analysis(APIKEY, SECRETKEY)

	while True:
		orders_id = trader.make_order(1000)
		trader.wait_close_position()
		for order in orders_id:
			trader.cancel_pending_order(order)
		time.sleep(5)


if __name__ == '__main__':
	main()

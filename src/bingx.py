import hmac
from hashlib import sha256
import requests
import time


class Bingx:
	def __init__(self, api, secret_key):
		self.api = api
		self.secret_key = secret_key
		self.api_url = "https://open-api-vst.bingx.com"
		self.total_volume = 0
		self.total_pnl = -1
		self.work = True

	def work_off(self):
		self.work = False

	def get_flag_work(self):
		return self.work

	def calculation_cost(self, pnl_from_trade):
		self.total_pnl += pnl_from_trade

	def calculation_volume(self, volume_from_trade):
		self.total_volume += volume_from_trade

	def get_total_volume(self):
		return self.total_volume

	def get_total_pnl(self):
		return self.total_pnl

	def set_position_mode(self):
		payload = {}
		path = '/openApi/swap/v1/positionSide/dual'
		method = "POST"
		paramsMap = {
			"dualSidePosition": "true"
		}
		paramsStr = self._parseParam(paramsMap)
		return self._send_request(method, path, paramsStr, payload)

	def __get_sign(self, api_secret, method, payload):
		signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"),
							 digestmod=sha256).hexdigest()  # Проверка целостности
		# print("sign=" + signature)
		return signature

	def _send_request(self, method, path, urlpa, payload):
		url = "%s%s?%s&signature=%s" % (self.api_url, path, urlpa, self.__get_sign(self.secret_key, method, urlpa))
		headers = {
			'X-BX-APIKEY': self.api,
		}
		response = requests.request(method, url, headers=headers, data=payload)
		# print(url)
		# print(response.text)
		return response

	def _parseParam(self, paramsMap):
		sortedKeys = sorted(paramsMap)
		paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
		if paramsStr != "":
			return paramsStr + "&timestamp=" + str(int(time.time() * 1000))
		else:
			return paramsStr + "timestamp=" + str(int(time.time() * 1000))

	def get_server_time(self):
		payload = {}
		path = '/openApi/swap/v2/server/time'
		method = "GET"
		paramsMap = {}
		paramsStr = self._parseParam(paramsMap)
		response = None
		check = 1
		while check != 0:
			try:
				response = self._send_request(method, path, paramsStr, payload)
				check = response.json()['code']
			except TimeoutError as s:
				print(s)
				time.sleep(3)
		return response.json()['data']['serverTime']


class Analysis(Bingx):
	def get_token_price(self, token):
		payload = {}
		path = '/openApi/swap/v1/ticker/price'
		method = "GET"
		data = []
		paramsMap = {
			"symbol": token,
			"timestamp": self.get_server_time()
		}
		paramsStr = self._parseParam(paramsMap)
		response = self._send_request(method, path, paramsStr, payload)
		print(float(response.json()['data']['price']))
		return float(response.json()['data']['price'])

	def get_trading_cost_and_volume(self, last_time_check):
		payload = {}
		path = '/openApi/swap/v2/trade/allOrders'
		method = "GET"
		paramsMap = {
			"startTime": last_time_check,
			"limit": "100",
		}
		paramsStr = self._parseParam(paramsMap)
		response = self._send_request(method, path, paramsStr, payload).json()
		print(response)
		cost = 0
		volume = 0
		last_check = last_time_check
		if (response['code'] == 0) and (response['data']['orders']):
			for i in response['data']['orders']:
				print('История', i)
			volume = sum([float(i['executedQty']) for i in response['data']['orders']
						 if i['time'] > last_time_check])
			cost = sum([float(i['profit'])+float(i['commission']) for i in response['data']['orders']
						if i['time'] > last_time_check])
			last_check = response['data']['orders'][-1]['time']
		return float('{:.4f}'.format(cost)), float('{:.4f}'.format(volume)), last_check

	def _get_take_profit(self, direction, entry_price, funding_rate, pnl):
		tp = 0.002
		# if (funding_rate > 0 and direction == 'LONG') or (funding_rate < 0 and direction == 'SHORT'):
		# 	tp += 0.0003
		if pnl < 0 and ((funding_rate > 0 and direction == 'SHORT') or (funding_rate < 0 and direction == 'LONG')):
			tp += 0.0005
		if direction == 'LONG':
			return entry_price * (1+tp)
		else:
			return entry_price * (1-tp)

	def _get_stop_loss(self, direction, entry_price):
		if direction == 'LONG':
			return entry_price * 0.9995
		else:
			return entry_price * 1.0005

	def _get_open_position(self, token):
		check = False
		payload = {}
		path = '/openApi/swap/v2/trade/openOrders'
		method = "GET"
		paramsMap = {
			"symbol": token,
			"recvWindow": "5000",
			"timestamp": self.get_server_time()
		}
		paramsStr = self._parseParam(paramsMap)
		return self._send_request(method, path, paramsStr, payload)

	def get_funding_rate(self, token):
		payload = {}
		path = '/openApi/swap/v2/quote/premiumIndex'
		method = "GET"
		paramsMap = {
			"symbol": token,
			"timestamp": self.get_server_time()
		}
		paramsStr = self._parseParam(paramsMap)
		response = self._send_request(method, path, paramsStr, payload)
		return float(response.json()['data']['lastFundingRate'])


class Trader(Analysis):
	def __init__(self, object, token, api, secret_key):
		super().__init__(api, secret_key)
		self.token = token
		self.object = object

	def make_order(self, volume_in_usdt):
		check, check1 = False, False
		funding_rate = self.get_funding_rate(self.token)
		total_pnl = self.get_total_pnl()
		payload = {}
		path = '/openApi/swap/v2/trade/order'
		method = "POST"
		directions = (('BUY', 'SELL'), ('LONG', 'SHORT'))
		while not check and not check1:
			for _ in range(5):
				price = self.get_token_price(self.token)
				volume_in_coin = float("{:.4f}".format(volume_in_usdt/price))
				data = []
				ordersId = []
				for i in range(2):
					TP = "{:.5f}".format(self._get_take_profit(directions[1][i], price, funding_rate, total_pnl))
					SL = "{:.5f}".format(self._get_stop_loss(directions[1][i], price))

					paramsMap = {
						"symbol": self.token,
						"side": directions[0][i],
						"positionSide": directions[1][i],
						"type": "LIMIT",
						"price": price,
						"quantity": volume_in_coin,
						"takeProfit": "{\"type\": \"TAKE_PROFIT_MARKET\", \"stopPrice\": %s,  \"price\": %s, \"workingType\":\"MARK_PRICE\"}" % (TP, TP),
						"stopLoss": "{\"type\": \"STOP_MARKET\", \"stopPrice\": %s, \"price\": %s, \"workingType\":\"MARK_PRICE\"}" % (SL, SL),
						"timestamp": self.get_server_time()
					}

					paramsStr = self._parseParam(paramsMap)
					response = self._send_request(method, path, paramsStr, payload)
					print(response.json())
					data.append(response)

					if response.json()['code'] == 0:
						ordersId.append(response.json()['data']['order']['orderId'])

					if response.json()['code'] != 0 and len(ordersId) == 0:
						break
					elif response.json()['code'] != 0 and len(ordersId) == 1:
						self._cancel_order(ordersId[0])
						break

				print(ordersId)
				if len(ordersId) == 2:  # Чекает все ли ордера открылись, если да, то выходит и больше не доебывается
					check = True
					check1 = True
				elif len(ordersId) == 1:
					self._cancel_order(ordersId[0])
					time.sleep(2)
				else:
					time.sleep(3)

				if check:
					break

			if check1 is False:
				time.sleep(10)

		return ordersId

	def wait_close_position(self):
		while True:
			positions = self._get_open_position(self.token).json()
			print('wait_close_position', positions)
			if positions['code'] == 0:
				types_of_positions = [positions['data']['orders'][i]['type']
									  for i in range(len(positions['data']['orders']))]
				# print(types_of_positions)
				if (not(positions['data']['orders'])) or \
						((len(types_of_positions) == 1) and (types_of_positions[0] == 'LIMIT')):
					break
			time.sleep(2)

	def cancel_pending_order(self, orderId):
		payload = {}
		path = '/openApi/swap/v2/trade/openOrder'
		method = "GET"
		paramsMap = {
			'orderId': orderId,
			"symbol": self.token,
			"recvWindow": "5000",
			"timestamp": self.get_server_time()
		}
		paramsStr = self._parseParam(paramsMap)
		response_pending_order = self._send_request(method, path, paramsStr, payload).json()
		print('response_pending_order', response_pending_order)
		print(response_pending_order['code'])
		if response_pending_order['code'] == 0:
			self._cancel_order(orderId)

	def cancel_all_orders(self):
		payload = {}
		path = '/openApi/swap/v2/trade/closeAllPositions'
		method = "POST"
		paramsMap = {
			"symbol": "BTC-USDT"
		}
		paramsStr = self._parseParam(paramsMap)
		return self._send_request(method, path, paramsStr, payload)

	def _cancel_order(self, orderID):
		payload = {}
		path = '/openApi/swap/v2/trade/order'
		method = "DELETE"
		paramsMap = {
			"orderId": orderID,
			"symbol": self.token,
			"timestamp": self.get_server_time()
		}
		paramsStr = self._parseParam(paramsMap)
		return self._send_request(method, path, paramsStr, payload)

	def set_leverage(self, leverage):
		data = []
		payload = {}
		path = '/openApi/swap/v2/trade/leverage'
		method = "POST"
		for side in ('LONG', 'SHORT'):
			paramsMap = {
				"leverage": leverage,
				"side": side,
				"symbol": self.token,
				"timestamp": self.get_server_time()
			}
			paramsStr = self._parseParam(paramsMap)
			data.append(self._send_request(method, path, paramsStr, payload))
		return data

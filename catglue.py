# catglue notifier v1
# programmed by dani, sep 02 2021

import os
import time
from requests import get, post

webhook_url = "-"
notifier_role = "-"

wait_time = 3600 # seconds. DON'T LOWER THIS WITHOUT ASKING ADAM
fail_time = 60 # seconds

colours = {
	"xs": 0xFFFFCE,
	"xp": 0xCECEFF,
	"xq": 0xCEFFCE,
	"yl": 0xFFCECE,
	"zz": 0xFFCEFF,
	"ov": 0xCECECE,
	"PA": 0xFFFFFF,
	"me": 0xCEFFFF
}

def rget(url): # get but it retries if fail
	backoff = fail_time
	while True:
		try:
			data = get(url)
			if data.status_code == 200:
				return data
		except:
			pass
		print("Server Error, sleeping for " + str(backoff) + " seconds...")
		time.sleep(backoff)
		backoff += fail_time

def notify(apgcode, occurrences, occurrences_old, symmetry): # notify about object
	print(apgcode, occurrences, occurrences_old, symmetry)

	samples = rget("https://catagolue.hatsya.com/textsamples/" + apgcode + "/b3s23")
	soup = samples.text.split(symmetry + "/")[-1].strip()

	# Get additional information
	
	soups = rget("https://catagolue.hatsya.com/attribute/" + apgcode + "/b3s23").text
	soup_index = soups.rfind(soup)
	if soup_index != -1:
		found, owner = soups.split(" on ")[-1].split(" and is owned by ")
		owner = owner.split("\n")[0]
		found.replace(" at ", "")
		if owner.find("@") > 2:
			owner = owner.split("@")[0]
	else:
		found = "???"
		owner = "???"

	embed = {
		"embeds": [{
			"title": "Object found!",
			"description": "An object with a low number of occurrences has been located." if occurrences_old != 0 else "An object with zero previous occurrences has been located!",
			"color": colours[apgcode[:2]],
			"footer": {
				"icon_url": "https://cdn.discordapp.com/avatars/876266072125358090/82e14c7e2b9e9bcc84b08c477007ec60.png",
				"text": "catgIue.py"
			},
			"image": {
				"url": "https://catagolue.appspot.com/pic/"+apgcode+"/b3s23"
			},
			"fields": [
				{
					"name": "apgcode",
					"value": "["+apgcode+"](https://catagolue.hatsya.com/object/"+apgcode+"/b3s23)",
					"inline": True
				},
				{
					"name": "Occurrences",
					"value": str(occurrences) + " (" + str(occurrences_old) + ")",
					"inline": True
				},
				{
					"name": "Symmetry",
					"value": symmetry,
					"inline": True
				},
				{
					"name": "Soup",
					"value": "["+soup+"](https://catagolue.hatsya.com/hashsoup/"+symmetry+"/"+soup+"/b3s23)",
					"inline": True
				},
				{
					"name": "Discoverer",
					"value": owner,
					"inline": True
				},
				{
					"name": "Time",
					"value": found,
					"inline": True
				}
			]
		}]
	}

	if occurrences_old == 0:
		embed["content"] = "<@&" + notifier_role + ">"

	response = post(webhook_url, json=embed) # should rpost be a thing? probably, but idk what discord uses for errors

def is_active(symmetry): # checks whether a given symmetry has been updated in the last wait_time
	data = rget("https://catagolue.hatsya.com/texthaul/b3s23/" + symmetry).text.split(" ")[2]
	last_haul = time.strptime(data, "%Y-%m-%dT%H:%M:%S")
	last_call = time.gmtime(time.time() - wait_time)
	return last_haul > last_call

def get_pop(apgcode): # gets population of apgcode. most of this code isn't used but i wrote anyway
	letters = "0123456789abcdefghijklmnopqrstuv"
	population, space = 0, 0
	if apgcode[:2] == "xs":
		return int(apgcode[2:apgcode.find("_")])
	elif apgcode[:2] in ["me", "ov", "PA", "yl", "zz"]:
		return 0
	code = apgcode.split("_")[1]

	for c in code:
		if c == "y" and space == 0:
			space = 1
		elif c not in "wxz" and space == 0:
			population += bin(letters.find(c)).count("1")
		elif space == 1:
			space = 0
	return population

def is_notable(apgcode, old_num, symmetry): # checks if object is notable
	population = get_pop(apgcode)
	prefix = apgcode[:2]
	# probably could do without duplicating the notability requirements but it's 4 am
	if symmetry == "C1" and ((prefix != "xs" and old_num < 10) or (prefix == "xs" and old_num < 10 and (population < 17 or population > 32))):
		return True
	elif symmetry == "G1" and ((prefix != "xs" and old_num < 10) or (prefix == "xs" and old_num < 10 and (population < 17 or population > 32))):
		samples = rget("https://catagolue.hatsya.com/textsamples/" + apgcode + "/b3s23").text
		if samples[:3] != "C1/" and samples.find("\nC1/") != -1:
			return True

def diff(symmetry): # compares textcensus files
	old = {i.split(",")[0][1:-1]: int(i.split(",")[1][1:-1]) for i in open(symmetry + "_old", "r").read().splitlines()[1:]}
	new = {i.split(",")[0][1:-1]: int(i.split(",")[1][1:-1]) for i in open(symmetry + "_new", "r").read().splitlines()[1:]}
	diff = {}
	for k in new:
		old_num = old.get(k, 0)
		diff[k] = new[k] - old_num
		# print(diff[k])
		if diff[k] == 0 or not is_notable(k, old_num, symmetry):
			diff.pop(k, None)
		else:
			notify(k, new[k], old_num, symmetry)

def get_new(symmetry): # gets new textcensus
	if os.path.exists(symmetry + "_old"):
		os.remove(symmetry + "_old")
	if os.path.exists(symmetry + "_new"):
		os.rename(symmetry + "_new", symmetry + "_old")
	open(symmetry + "_new", "w+").write(rget("https://catagolue.hatsya.com/textcensus/b3s23/" + symmetry).text)
	if os.path.exists(symmetry + "_old"):
		diff(symmetry)

symmetries = ["C1", "G1"]

while True:
	time.sleep(wait_time - time.time()%wait_time)
	for symmetry in symmetries:
		if is_active(symmetry):
			get_new(symmetry)
			print("Got " + symmetry)
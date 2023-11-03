import json
from bson import ObjectId
from src.models.viewer import *
from src.features import *
from src.basics import *
from src.download_driver import *
from src.load_files import *
from src.colors import *
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
from undetected_chromedriver.patcher import Patcher
from requests.exceptions import RequestException
from random import choice, randint
from time import gmtime, sleep, strftime, time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from celery import Celery
from fake_headers import Headers, browsers
from datetime import datetime
import shutil
import subprocess
import psutil
import requests
import re
import pymongo
import ssl
import random
import dns.resolver

import certifi
ca = certifi.where()


driver_dict = {}
duration_dict = {}
temp_folders = []

summary = {}

view = []

used_profiles = []

suggested = []

playback_speed = 1

animation = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]
headers_1 = ['Worker', 'Video Title', 'Watch / Actual Duration']
headers_2 = ['Index', 'Video Title', 'Views']

width = 0
max_threads = 2
worker_concurrency = 5

load_dotenv()

RABBITMQ_URI = os.environ.get("RABBITMQ_URI")
MONGODB_CONNECTION_URI = os.environ.get("MONGODB_CONNECTION_URI")
IS_DEBUG = os.environ.get("IS_DEBUG")
PROFILE_PATH = os.environ.get("PROFILE_PATH")

celery = Celery(
    __name__,
    broker=RABBITMQ_URI,
    worker_concurrency=worker_concurrency,
    broker_use_ssl={
        'keyfile': None,
        'certfile': None,
        'ca_certs': None,
        'cert_reqs': ssl.CERT_NONE  # Ignore certificate verification
    }
)

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

client = pymongo.MongoClient(MONGODB_CONNECTION_URI, tlsCAFile=ca)
db = client["youtube_viewer"]


@celery.task(bind=True)
def viewer(self, bot_id, views_per_task, proxy, video_url, keywords, video_title, filter_by):
    global bot, max_threads, view, used_profiles
    task_id = self.request.id

    bot_id = ObjectId(bot_id)

    bot = db["bots"].find_one({"_id": bot_id})

    setup_chrome_driver()

    db["tasks"].update_one(
        {"_id": task_id},
        {"$set":
            {
                "status": 1,
            }
         }
    )

    db["bots"].update_one(
        {"_id": bot_id},
        {"$set":
            {
                "status": 1,
            }
         }
    )

    if int(IS_DEBUG) == 0:
        res = change_ip(proxy["url"], proxy["port"])
        sleep(20)

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        proxy_link = f"{proxy['username']}:{proxy['password']}@{proxy['url']}:{proxy['port']}"
        futures = [executor.submit(view_video, bot_id, task_id, position, proxy_link, video_url, keywords, video_title, filter_by)
                   for position in range(views_per_task)]

        wait(futures)
        print('All tasks are done!')

        db["tasks"].update_one(
            {"_id": task_id},
            {"$set":
                {
                    "status": 2,
                }
             }
        )

        update_bot_status(bot_id)
        used_profiles = []

        return "Succeeded"


def update_bot_status(bot_id):
    bot = db["bots"].find_one({"_id": bot_id})
    completed_tasks = int(bot["completed_tasks"]) + 1
    db["bots"].update_one(
        {"_id": bot_id},
        {"$set":
            {
                "completed_tasks": completed_tasks,
            }
         }
    )
    if completed_tasks >= int(bot["total_tasks"]) or int(bot["target_viewed"]) >= int(bot["target_views"]):
        db["bots"].update_one(
            {"_id": bot_id},
            {"$set":
                {
                    "status": 2,
                    "finish_time": datetime.now()
                }
             }
        )


def view_video(bot_id, task_id, position, proxy_link, video_url, keywords, video_title, filter_by):
    global width, created_viewer
    driver = None
    data_dir = None
    profile = None
    email = None

    viewer = jsonable_encoder(
        ViewerModel(
            task_id=task_id,
            position=position,
            start_time=datetime.now(),
            status=1
        )
    )

    created_viewer = db["viewers"].insert_one(viewer)

    try:
        header = Headers(
            browser="chrome",
            os=osname,
            headers=False
        ).generate()
        agent = header['User-Agent']

        db["viewers"].update_one(
            {"_id": created_viewer.inserted_id},
            {"$set":
                {
                    "start_time": datetime.now()
                }
             }
        )

        url, keyword, method, youtube = choose_method(
            position, video_url, keywords)

        try:
            print(timestamp() + bcolors.OKBLUE + f"Worker {position} | " + bcolors.OKGREEN +
                  f"{proxy_link} | Good Proxy | Opening a new driver..." + bcolors.ENDC)

            print("patched_drivers",
                  f'chromedriver_{position%max_threads}{exe_name}')

            patched_driver = os.path.join(
                patched_drivers, f'chromedriver_{position%max_threads}{exe_name}')

            try:
                Patcher(executable_path=patched_driver).patch_exe()
            except Exception:
                pass

            factor = int(max_threads/(0.1*max_threads + 1))
            sleep_time = int((str(position)[-1])) * factor
            sleep(sleep_time)

            viewports = list(db["configs"].find_one(
                {"key": "viewports"})["value"])

            profile = get_profile()

            # email = get_email()
            print("---------------")
            print(patched_driver)
            print("---------------")
            driver = get_driver(False, viewports, agent,
                                True, patched_driver, proxy_link, profile)

            if not profile:
                data_dir = driver.capabilities['chrome']['userDataDir']
                temp_folders.append(data_dir)

            sleep(2)

            if int(IS_DEBUG) == 0:
                spoof_geolocation(proxy_link, driver)

            if width == 0:
                width = driver.execute_script('return screen.width')
                height = driver.execute_script('return screen.height')
                print(f'Display resolution : {width}x{height}')
                viewports = [i for i in viewports if int(i[:4]) <= width]

            set_referer(position, url, method, driver)

            if 'consent' in driver.current_url:
                print(timestamp() + bcolors.OKBLUE +
                      f"Worker {position} | Bypassing consent..." + bcolors.ENDC)

                bypass_consent(driver)

            if video_title:
                output = video_title
            else:
                output = driver.title[:-10]

            if youtube == 'Video':
                view_stat = youtube_normal(
                    method, keyword, video_title, driver, output, filter_by)
            else:
                view_stat, output = youtube_music(driver)

            if 'watching' in view_stat:
                youtube_live(proxy_link, position, driver,
                             output, bot_id, task_id)

            else:
                current_url, current_channel = music_and_video(
                    proxy_link, position, youtube, driver, output, view_stat, created_viewer.inserted_id, bot_id, task_id)

            channel_or_endscreen(proxy_link, position, youtube,
                                 driver, view_stat, current_url, current_channel, created_viewer.inserted_id, bot_id, task_id)

            if randint(1, 2) == 1:
                try:
                    driver.find_element(By.ID, 'movie_player').send_keys('k')
                except WebDriverException:
                    pass

            remove_used_profile(profile=profile)
            # update_email_status(email=email, status=1)
            status = quit_driver(driver=driver, data_dir=data_dir)

            db["viewers"].update_one(
                {"_id": created_viewer.inserted_id},
                {"$set":
                    {
                        "finish_time": datetime.now(),
                        "status": 2
                    }
                 }
            )

        except Exception as e:
            remove_used_profile(profile=profile)
            # update_email_status(email=email, status=1)
            status = quit_driver(driver=driver, data_dir=data_dir)

            print(timestamp() + bcolors.FAIL +
                  f"Worker {position} | Line : {e.__traceback__.tb_lineno} | {type(e).__name__} | {e.args[0] if e.args else ''}" + bcolors.ENDC)

            db["viewers"].update_one(
                {"_id": created_viewer.inserted_id},
                {"$set":
                    {
                        "finish_time": datetime.now(),
                        "status": 3,
                        "description": f"Line : {e.__traceback__.tb_lineno} | {type(e).__name__}"
                    }
                 }
            )

    except RequestException:
        print(timestamp() + bcolors.OKBLUE + f"Worker {position} | " +
              bcolors.FAIL + f"{proxy_link} | Bad proxy " + bcolors.ENDC)

        db["viewers"].update_one(
            {"_id": created_viewer.inserted_id},
            {"$set":
             {
                 "finish_time": datetime.now(),
                 "status": 3,
                 "description": f"{proxy_link} | Bad proxy "
             }
             }
        )

    except Exception as e:
        print(timestamp() + bcolors.FAIL +
              f"Worker {position} | Line : {e.__traceback__.tb_lineno} | {type(e).__name__} | {e.args[0] if e.args else ''}" + bcolors.ENDC)

        db["viewers"].update_one(
            {"_id": created_viewer.inserted_id},
            {"$set":
             {
                 "finish_time": datetime.now(),
                 "status": 3,
                 "description": f"Line : {e.__traceback__.tb_lineno} | {type(e).__name__}"
             }
             }
        )


def choose_method(position, video_url, keywords):
    url = None
    keyword = None

    if position % 5 == 0:
        try:
            method = 1
            url = video_url
            if 'music.youtube.com' in url:
                youtube = 'Music'
            else:
                youtube = 'Video'
        except IndexError:
            raise Exception("Your urls.txt is empty!")
    else:
        try:
            method = 2
            keyword = choice(keywords)
            url = "https://www.youtube.com"
            youtube = 'Video'
        except IndexError:
            try:
                youtube = 'Music'
                url = video_url
                if 'music.youtube.com' not in url:
                    raise Exception
            except Exception:
                raise Exception("Your search.txt is empty!")

    return url, keyword, method, youtube


def get_email():
    email = None
    email_list = list(db["emails"].find({"status": 1}))
    email = choice(email_list)

    update_email_status(email=email, status=2)

    return email


def get_profile():
    profile = None
    profiles = os.listdir(PROFILE_PATH)

    i = 0
    while i < len(profiles):
        p = choice(profiles)
        if p not in used_profiles:
            used_profiles.append(p)
            profile = p
            break
        i += 1
    return profile


def change_ip(url, port):
    payload = json.dumps({
        "ip": url,
        "port": port
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.post(
        f"http://{url}:3001/device/youtube-bot-rotate", headers=headers, data=payload)

    return response


def spoof_geolocation(proxy_link, driver):
    try:
        proxy_dict = {
            "http": f"http://{proxy_link}",
                    "https": f"http://{proxy_link}",
        }
        resp = requests.get(
            "http://ip-api.com/json", proxies=proxy_dict, timeout=30)

        if resp.status_code == 200:
            location = resp.json()
            params = {
                "latitude": location['lat'],
                "longitude": location['lon'],
                "accuracy": randint(20, 100)
            }
            driver.execute_cdp_cmd(
                "Emulation.setGeolocationOverride", params)

    except (RequestException, WebDriverException):
        pass


def set_referer(position, url, method, driver):
    # referers = list(db["configs"].find_one({"key": "referers"})["value"])

    url = os.environ.get("API_ENDPOINT")+"/system-config/bot/referer"
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    payload = {}
    headers = {'bot-token': BOT_TOKEN}

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code == 200:

        data = response.text
        referers = json.loads(data)
        referer = choice(referers['value'])

        if referer:
            if method == 2 and 't.co/' in referer:
                driver.get(url)
            else:
                if 'search.yahoo.com' in referer:
                    driver.get('https://duckduckgo.com/')
                    driver.execute_script(
                        "window.history.pushState('page2', 'Title', arguments[0]);", referer)
                else:
                    driver.get(referer)

                driver.execute_script(
                    "window.location.href = '{}';".format(url))

            print(timestamp() + bcolors.OKBLUE +
                  f"Worker {position} | Referer used : {referer}" + bcolors.ENDC)

        else:
            driver.get(url)


def youtube_normal(method, keyword, video_title, driver, output, filter_by):
    if method == 2:
        msg = search_video(driver, keyword, video_title, filter_by)
        if msg == 'failed':
            raise Exception(
                f"Can't find this [{video_title}] video with this keyword [{keyword}]")

    skip_initial_ad(driver, output, duration_dict)

    try:
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located(
            (By.ID, 'movie_player')))
    except WebDriverException:
        raise Exception(
            "Slow internet speed or Stuck at reCAPTCHA! Can't load YouTube...")

    features(driver)

    try:
        view_stat = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#count span'))).text
        if not view_stat:
            raise WebDriverException
    except WebDriverException:
        view_stat = driver.find_element(
            By.XPATH, '//*[@id="info"]/span[1]').text

    return view_stat


def youtube_music(driver):
    if 'coming-soon' in driver.title or 'not available' in driver.title:
        raise Exception(
            "YouTube Music is not available in your area!")
    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
            (By.XPATH, '//*[@id="player-page"]')))
    except WebDriverException:
        raise Exception(
            "Slow internet speed or Stuck at reCAPTCHA! Can't load YouTube...")

    bypass_popup(driver)

    play_music(driver)

    output = driver.find_element(
        By.XPATH, '//ytmusic-player-bar//yt-formatted-string').text
    view_stat = 'music'

    return view_stat, output


def youtube_live(proxy_link, position, driver, output, bot_id, task_id):
    error = 0
    while True:
        view_stat = driver.find_element(
            By.CSS_SELECTOR, '#count span').text
        if 'watching' in view_stat:
            print(timestamp() + bcolors.OKBLUE + f"Worker {position} | " + bcolors.OKGREEN +
                  f"{proxy_link} | {output} | " + bcolors.OKCYAN + f"{view_stat} " + bcolors.ENDC)
        else:
            error += 1

        play_video(driver)

        random_command(driver)

        if error == 5:
            break
        sleep(60)

    update_view_count(position, bot_id, task_id)


def music_and_video(proxy_link, position, youtube, driver, output, view_stat, viewer_id, bot_id, task_id):
    rand_choice = 1
    if len(suggested) > 1 and view_stat != 'music':
        rand_choice = randint(1, 3)

    for i in range(rand_choice):
        if i == 0:
            current_url, current_channel = control_player(
                driver, output, position, proxy_link, youtube, viewer_id, collect_id=True)

            update_view_count(position, bot_id, task_id)

        else:
            print(timestamp() + bcolors.OKBLUE +
                  f"Worker {position} | Suggested video loop : {i}" + bcolors.ENDC)

            try:
                output = go_next_video(driver, suggested)
            except WebDriverException as e:
                raise Exception(
                    f"Error suggested | {type(e).__name__} | {e.args[0] if e.args else ''}")

            print(timestamp() + bcolors.OKBLUE +
                  f"Worker {position} | Found next suggested video : [{output}]" + bcolors.ENDC)

            skip_initial_ad(driver, output, duration_dict)

            features(driver)

            current_url, current_channel = control_player(
                driver, output, position, proxy_link, youtube, viewer_id, collect_id=False)

            update_view_count(position, bot_id, task_id)

    return current_url, current_channel


def channel_or_endscreen(proxy_link, position, youtube, driver, view_stat, current_url, current_channel, viewer_id, bot_id, task_id):
    option = 1
    if view_stat != 'music' and driver.current_url == current_url:
        option = choices([1, 2, 3], cum_weights=(0.5, 0.75, 1.00), k=1)[0]

        if option == 2:
            try:
                output, log, option = play_from_channel(
                    driver, current_channel)
            except WebDriverException as e:
                raise Exception(
                    f"Error channel | {type(e).__name__} | {e.args[0] if e.args else ''}")

            print(timestamp() + bcolors.OKBLUE +
                  f"Worker {position} | {log}" + bcolors.ENDC)

        elif option == 3:
            try:
                output = play_end_screen_video(driver)
            except WebDriverException as e:
                raise Exception(
                    f"Error end screen | {type(e).__name__} | {e.args[0] if e.args else ''}")

            print(timestamp() + bcolors.OKBLUE +
                  f"Worker {position} | Video played from end screen : [{output}]" + bcolors.ENDC)

        if option in [2, 3]:
            skip_initial_ad(driver, output, duration_dict)

            features(driver)

            current_url, current_channel = control_player(
                driver, output, position, proxy_link, youtube, viewer_id, collect_id=False)

        if option in [2, 3, 4]:
            update_view_count(position, bot_id, task_id)


def features(driver):
    if bot["save_bandwidth"]:
        save_bandwidth(driver)

    bypass_popup(driver)

    bypass_other_popup(driver)

    play_video(driver)

    change_playback_speed(driver, playback_speed)


def control_player(driver, output, position, proxy_link, youtube, viewer_id, collect_id=True):
    current_url = driver.current_url

    video_len = duration_dict.get(output, 0)
    for _ in range(90):
        if video_len != 0:
            duration_dict[output] = video_len
            break

        video_len = driver.execute_script(
            "return document.getElementById('movie_player').getDuration()")
        sleep(1)

    if video_len == 0:
        raise Exception('Video player is not loading...')

    actual_duration = strftime(
        "%Hh:%Mm:%Ss", gmtime(video_len)).lstrip("0h:0m:")
    watching_video_len = video_len*uniform(bot["minimum"], bot["maximum"])
    duration = strftime("%Hh:%Mm:%Ss", gmtime(
        watching_video_len)).lstrip("0h:0m:")

    summary[position] = [position, output, f'{duration} / {actual_duration}']

    db["viewers"].update_one(
        {"_id": viewer_id},
        {"$set":
            {
                "video_duration": f'{video_len:.0f}',
                "watching_duration": f'{watching_video_len:.0f}'
            }
         }
    )

    print(timestamp() + bcolors.OKBLUE + f"Worker {position} | " + bcolors.OKGREEN +
          f"{proxy_link} --> {youtube} Found : {output} | Watch Duration : {duration} " + bcolors.ENDC)

    if youtube == 'Video' and collect_id:
        try:
            video_id = re.search(
                r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", current_url).group(1)
            if video_id not in suggested and output in driver.title:
                suggested.append(video_id)
        except Exception:
            pass

    try:
        current_channel = driver.find_element(
            By.CSS_SELECTOR, '#upload-info a').text
    except WebDriverException:
        current_channel = 'Unknown'

    error = 0
    loop = int(video_len/4)
    for _ in range(loop):
        sleep(5)
        current_time = driver.execute_script(
            "return document.getElementById('movie_player').getCurrentTime()")

        if youtube == 'Video':
            play_video(driver)
            random_command(driver)
        elif youtube == 'Music':
            play_music(driver)

        current_state = driver.execute_script(
            "return document.getElementById('movie_player').getPlayerState()")
        if current_state in [-1, 3]:
            error += 1
        else:
            error = 0

        if error == 10:
            error_msg = f'Taking too long to play the video | Reason : buffering'
            if current_state == -1:
                error_msg = f"Failed to play the video | Possible Reason : {proxy_link} not working anymore"
            raise Exception(error_msg)

        elif current_time > watching_video_len or driver.current_url != current_url:
            break

    summary.pop(position, None)

    return current_url, current_channel


def update_view_count(position, bot_id, task_id):
    view.append(position)
    view_count = len(view)
    bot = db["bots"].find_one({"_id": bot_id})
    bot_target_viewed = int(bot["target_viewed"]) + 1
    db["bots"].update_one(
        {"_id": bot_id},
        {"$set":
            {
                "target_viewed": bot_target_viewed,
            }
         }
    )

    task = db["tasks"].find_one({"_id": task_id})
    db["tasks"].update_one(
        {"_id": task_id},
        {"$set":
            {
                "viewed": int(task["viewed"]) + 1,
            }
         }
    )
    if bot_target_viewed >= int(bot["target_views"]):
        tasks = list(db["tasks"].find({"bot_id": bot_id}))
        for task in tasks:
            celery.control.revoke(task["_id"])

    print(timestamp() + bcolors.OKCYAN +
          f'Worker {position} | View added : {view_count}' + bcolors.ENDC)


def timestamp():
    global date_fmt
    date_fmt = datetime.now().strftime("%d-%b-%Y %H:%M:%S")
    cpu_usage = str(psutil.cpu_percent(1))
    return bcolors.OKGREEN + f'[{date_fmt}] | ' + bcolors.OKCYAN + f'{cpu_usage} | '


def remove_used_profile(profile):
    if profile and profile in used_profiles:
        used_profiles.remove(profile)


def update_email_status(email, status):
    db["emails"].update_one(
        {"username": email["username"]},
        {"$set":
            {
                "status": status,
            }
         }
    )


def quit_driver(driver, data_dir):
    if driver:
        driver.quit()
        if data_dir in temp_folders:
            temp_folders.remove(data_dir)

    status = 400
    return status


def setup_chrome_driver():
    global osname, exe_name, cwd, patched_drivers
    cwd = os.getcwd()
    patched_drivers = os.path.join(cwd, 'patched_drivers')
    osname, exe_name = download_driver(patched_drivers=patched_drivers)
    copy_drivers(cwd=cwd, patched_drivers=patched_drivers,
                 exe=exe_name, total=4)

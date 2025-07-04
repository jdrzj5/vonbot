import discord
from discord.ext import commands, tasks
import os
import json
import datetime
from datetime import date
from keep_alive import keep_alive
from dotenv import load_dotenv
from datetime import datetime, timedelta
from discord import ui, Interaction
from discord.ui import View, Button, Select
from discord import Embed
import discord
import uuid

last_rp_year = None
load_dotenv()
keep_alive()


def has_role(member, role_id=1389959233461682256):
    return any(role.id == role_id for role in member.roles)


# --- RP year settings ---
rp_start_year = 1904
start_date = date(2025, 7, 1)
current_rp_year = rp_start_year + (date.today() - start_date).days
channel_id = 1389937231866757151  # Wstaw tutaj ID kanału na którym ma się wysyłać rok RP

# --- Intents & bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- Plik z danymi ---
users_file = "users.json"
alliances_file = "alliances.json"


def json_converter(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"Nie mogę serializować obiektu typu {type(o)}")


def load_data():
    try:
        with open(users_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(
            "Błąd: plik JSON jest uszkodzony lub pusty. Tworzę nowy pusty słownik."
        )
        return {}
    except FileNotFoundError:
        print("Plik nie istnieje, tworzę nowy pusty słownik.")
        return {}


def save_data(data):

    def json_converter(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()  # zamienia date/datetime na string ISO
        raise TypeError(f"Nie mogę serializować obiektu typu {type(o)}")

    with open(users_file, "w") as f:
        json.dump(data, f, indent=4, default=json_converter)


def load_alliances():
    try:
        with open(alliances_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(
            "Błąd: plik alliances.json nie istnieje lub jest uszkodzony. Tworzę nowy pusty słownik."
        )
        return {}


def save_alliances(data):

    def json_converter(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        raise TypeError(f"Nie mogę serializować obiektu typu {type(o)}")

    with open(alliances_file, "w") as f:
        json.dump(data, f, indent=4, default=json_converter)


users = load_data()
alliances = load_alliances()
pending_join_requests = {}
units = {
    "Piechota liniowa": 2,
    "Kawaleria lekka": 4,
    "Kawaleria ciężka": 6,
    "Piechota ciężka": 8,
    "Lekkie działo": 10,
    "Czołg lekki": 12,
    "Ciężkie działo": 14,
    "Czołg średni": 16,
    "Czołg ciężki": 18,
    "Statek transportowy": 3,
    "Krążownik": 6,
    "Niszczyciel": 12,
    "Pancernik": 21,
    "Sterowiec bombowy": 16,
}
units_land = {
    "Piechota liniowa", "Kawaleria lekka", "Kawaleria ciężka",
    "Piechota ciężka", "Lekkie działo", "Czołg lekki", "Ciężkie działo",
    "Czołg średni", "Czołg ciężki"
}
units_sea = {"Statek transportowy", "Krążownik", "Niszczyciel", "Pancernik"}

units_air = {"Sterowiec bombowy"}

technologies = {
    "Piechota liniowa": {
        "days": 0,
        "requires": []
    },
    "Piechota ciężka": {
        "days": 1,
        "requires": ["Piechota lekka"]
    },
    "Kawaleria lekka": {
        "days": 0,
        "requires": []
    },
    "Kawaleria ciężka": {
        "days": 1,
        "requires": ["Kawaleria lekka"]
    },
    "Lekkie działo": {
        "days": 0,
        "requires": []
    },
    "Ciężkie działo": {
        "days": 2,
        "requires": ["Lekkie działo"]
    },
    "Czołg lekki": {
        "days": 2,
        "requires": [],
        "year_required": 1916
    },
    "Czołg średni": {
        "days": 3,
        "requires": ["Czołg lekki"],
        "year_required": 1916
    },
    "Czołg ciężki": {
        "days": 5,
        "requires": ["Czołg średni"],
        "year_required": 1916
    },
    "Statek transportowy": {
        "days": 0,
        "requires": []
    },
    "Krążownik": {
        "days": 2,
        "requires": ["Statek transportowy"]
    },
    "Niszczyciel": {
        "days": 3,
        "requires": ["Krążownik"]
    },
    "Pancernik": {
        "days": 5,
        "requires": ["Niszczyciel"]
    },
    "Sterowiec bombowy": {
        "days": 4,
        "requires": []
    },
}

default_done = {
    "Piechota liniowa", "Kawaleria lekka", "Statek transportowy",
    "Lekkie działo"
}


def init_user(user_id):
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {
            "punkty": 0,
            "fabryki": 0,
            "ostatni_daily": None,
            "relacje": {},
            "cechy": [],
            "wojsko": {
                unit: 0
                for unit in units
            },
            "badania": {},
            "last_badanie_date": None,
            "alliance_id": None,  # <-- dodaj tutaj
        }
    else:
        if "relacje" not in users[user_id]:
            users[user_id]["relacje"] = {}
        if "cechy" not in users[user_id]:
            users[user_id]["cechy"] = []
        if "wojsko" not in users[user_id]:
            users[user_id]["wojsko"] = {unit: 0 for unit in units}
        if "badania" not in users[user_id]:
            users[user_id]["badania"] = {}
        if "last_badanie_date" not in users[user_id]:
            users[user_id]["last_badanie_date"] = None
        if "alliance_id" not in users[user_id]:  # <-- i tutaj
            users[user_id]["alliance_id"] = None

    for tech in default_done:
        if tech not in users[user_id]["badania"]:
            users[user_id]["badania"][tech] = {
                "status": "done",
                "start_date": None,
                "end_date": None
            }


# --- Eventy i komendy ---
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")
    daily_update.start()


army_data = {}


class WojskoView(ui.View):

    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid
        init_user(uid)
        user_data = users[uid]

        print("Badania użytkownika:", user_data["badania"])
        print("Lista jednostek:", units)

        for unit in units:
            badanie = user_data["badania"].get(unit)
            print(f"Sprawdzam jednostkę {unit}: badanie = {badanie}")
            if badanie and badanie.get("status") == "done":
                print(f"Dodaję przycisk dla {unit}")
                self.add_item(BuyButton(unit, uid))

        self.add_item(StatusButton(uid))


class BuyButton(ui.Button):

    def __init__(self, unit_name, uid):
        super().__init__(label=unit_name, style=discord.ButtonStyle.primary)
        self.unit_name = unit_name
        self.uid = uid

    async def callback(self, interaction: Interaction):
        user_data = users[self.uid]
        # Sprawdź czy jednostka jest odblokowana przez badanie
        badanie = user_data["badania"].get(self.unit_name)
        if not badanie or badanie.get("status") != "done":
            await interaction.response.send_message(
                f"Nie możesz kupić jednostki **{self.unit_name}**, ponieważ nie została jeszcze zbadana.",
                ephemeral=True)
            return

        cena = units[self.unit_name]
        if user_data["punkty"] >= cena:
            user_data["punkty"] -= cena
            user_data["wojsko"][self.unit_name] += 1
            save_data(users)
            await interaction.response.send_message(
                f"Kupiłeś 1x {self.unit_name} za {cena} punktów. Masz teraz {user_data['punkty']} punktów.",
                ephemeral=True)
        else:
            await interaction.response.send_message(
                "Nie masz wystarczająco punktów, aby kupić tę jednostkę.",
                ephemeral=True)


class StatusButton(ui.Button):

    def __init__(self, uid):
        super().__init__(label="Sprawdź stan wojska",
                         style=discord.ButtonStyle.secondary)
        self.uid = uid

    async def callback(self, interaction: Interaction):
        user_data = users[self.uid]
        wojsko = user_data["wojsko"]
        status = "\n".join(f"{unit}: {count}"
                           for unit, count in wojsko.items() if count > 0)
        if not status:
            status = "Nie posiadasz żadnych jednostek."
        await interaction.response.send_message(
            f"Stan twojego wojska:\n{status}", ephemeral=True)


@tasks.loop(minutes=1)
async def daily_update():
    global current_rp_year, last_rp_year

    # Sprawdź aktualny czas UTC
    now_utc = datetime.utcnow()

    # Jeśli jest dokładnie północ UTC (lub po niej, ale nie dalej niż 1 minuta)
    if now_utc.hour == 0 and now_utc.minute == 0:
        current_rp_year = rp_start_year + (date.today() - start_date).days
        if current_rp_year != last_rp_year:
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(f'📅 Rok RP: {current_rp_year}')
                last_rp_year = current_rp_year
            else:
                print(f"Nie znaleziono kanału o ID {channel_id}")


@bot.command()
async def rp_year(ctx):
    await ctx.send(f'Obecny rok RP to {current_rp_year}')


@bot.command()
async def daily(ctx):
    if not has_role(ctx.author):
        await ctx.send(
            f"{ctx.author.mention}, nie masz wymaganej roli, aby korzystać z tej komendy."
        )
        return

    uid = str(ctx.author.id)
    init_user(uid)

    today_str = datetime.utcnow().date().isoformat()
    ostatni_daily = users[uid].get("ostatni_daily", "")

    if ostatni_daily == today_str:
        await ctx.send(
            f"{ctx.author.mention}, już dzisiaj odebrałeś codzienne punkty!")
        return

    # Oblicz punkty
    base = 10
    bonus_fabryki = users[uid].get("fabryki", 0)

    # Liczenie aktywnych cech
    cechy = users[uid].get("cechy", [])
    today = date.today()
    suma_cech = 0
    aktywne_cechy = []

    updated_cechy = []
    for cecha in cechy:
        nadana = datetime.strptime(cecha["nadana"], "%Y-%m-%d").date()
        czas = cecha.get("czas", None)

        aktywna = True
        if czas is not None:
            if (today - nadana).days >= czas:
                aktywna = False

        if aktywna:
            aktywne_cechy.append(f"{cecha['nazwa']}: {cecha['wartosc']} pkt")
            suma_cech += cecha["wartosc"]
            updated_cechy.append(cecha)

    users[uid]["cechy"] = updated_cechy

    # Zapisz datę odebrania
    users[uid]["ostatni_daily"] = today_str
    users[uid]["punkty"] += base + bonus_fabryki + suma_cech
    save_data(users)

    opis_cech = "\n".join(
        aktywne_cechy) if aktywne_cechy else "Brak aktywnych cech."
    await ctx.send(
        f"{ctx.author.mention}, otrzymujesz **{base + bonus_fabryki + suma_cech} punktów**!\n"
        f"🏭 Fabryki: {bonus_fabryki} pkt\n"
        f"✨ Cechy:\n{opis_cech}")


@bot.command()
async def wojsko(ctx):
    uid = str(ctx.author.id)
    init_user(uid)
    view = WojskoView(uid)
    await ctx.send(
        f"{ctx.author.mention}, oto panel zarządzania wojskiem. Wybierz co chcesz zrobić:",
        view=view)


def is_admin(ctx):
    return ctx.author.guild_permissions.administrator


class ArmyView(View):

    def __init__(self, user_id: str):
        super().__init__(timeout=120)
        self.user_id = user_id

        # Dropdown z jednostkami
        self.unit_select = Select(placeholder="Wybierz jednostkę",
                                  options=[
                                      discord.SelectOption(label=unit,
                                                           value=unit)
                                      for unit in units
                                  ])
        self.unit_select.callback = self.unit_select_callback
        self.add_item(self.unit_select)

        # Dropdown z ilościami
        amounts = [1, 5, 10, 20, 40]
        self.amount_select = Select(placeholder="Wybierz ilość",
                                    options=[
                                        discord.SelectOption(label=str(a),
                                                             value=str(a))
                                        for a in amounts
                                    ])
        self.amount_select.callback = self.amount_select_callback
        self.add_item(self.amount_select)

        # Domyślne wartości
        self.selected_unit = None
        self.selected_amount = 1

    async def unit_select_callback(self, interaction: discord.Interaction):
        self.selected_unit = self.unit_select.values[0]
        await interaction.response.send_message(
            f"Wybrano jednostkę: {self.selected_unit}", ephemeral=True)

    async def amount_select_callback(self, interaction: discord.Interaction):
        self.selected_amount = int(self.amount_select.values[0])
        await interaction.response.send_message(
            f"Wybrano ilość: {self.selected_amount}", ephemeral=True)

    @discord.ui.button(label="Dodaj jednostki",
                       style=discord.ButtonStyle.green)
    async def add_units(self, interaction: discord.Interaction,
                        button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Nie masz uprawnień do tego.", ephemeral=True)
            return
        if not self.selected_unit:
            await interaction.response.send_message("Musisz wybrać jednostkę.",
                                                    ephemeral=True)
            return

        user_data = users[self.user_id]
        user_data["wojsko"][self.selected_unit] += self.selected_amount
        await self.update_message(
            interaction,
            f"Dodano {self.selected_amount}x {self.selected_unit}")

    @discord.ui.button(label="Usuń jednostki", style=discord.ButtonStyle.red)
    async def remove_units(self, interaction: discord.Interaction,
                           button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Nie masz uprawnień do tego.", ephemeral=True)
            return
        if not self.selected_unit:
            await interaction.response.send_message("Musisz wybrać jednostkę.",
                                                    ephemeral=True)
            return

        user_data = users[self.user_id]
        current = user_data["wojsko"].get(self.selected_unit, 0)
        user_data["wojsko"][self.selected_unit] = max(
            0, current - self.selected_amount)
        await self.update_message(
            interaction,
            f"Usunięto {self.selected_amount}x {self.selected_unit}")

    async def update_message(self, interaction: discord.Interaction,
                             info_msg: str):
        user_data = users[self.user_id]
        wojsko = user_data["wojsko"]
        status = "\n".join(f"{unit}: {count}"
                           for unit, count in wojsko.items() if count > 0)
        if not status:
            status = "Nie posiadasz żadnych jednostek."

        embed = discord.Embed(
            title=f"Stan wojska użytkownika <@{self.user_id}>",
            description=status,
            color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=self)
        # dodatkowa odpowiedź (można usunąć jeśli nie chcesz wiadomości ephemeral)
        await interaction.followup.send(info_msg, ephemeral=True)


class AddUnitButton(Button):

    def __init__(self, unit_name, user_id):
        super().__init__(style=discord.ButtonStyle.green,
                         label=f"+ {unit_name}",
                         custom_id=f"add_{unit_name}_{user_id}")
        self.unit_name = unit_name
        self.user_id = user_id

    async def callback(self, interaction):
        # Sprawdzenie uprawnień administratora
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Nie masz uprawnień do tej akcji.", ephemeral=True)
            return

        user_data = users[self.user_id]
        user_data["wojsko"][self.unit_name] += 1
        save_data(users)

        await self.view.update_embed(interaction)


class RemoveUnitButton(Button):

    def __init__(self, unit_name, user_id):
        super().__init__(style=discord.ButtonStyle.red,
                         label=f"- {unit_name}",
                         custom_id=f"remove_{unit_name}_{user_id}")
        self.unit_name = unit_name
        self.user_id = user_id

    async def callback(self, interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Nie masz uprawnień do tej akcji.", ephemeral=True)
            return

        user_data = users[self.user_id]
        if user_data["wojsko"].get(self.unit_name, 0) > 0:
            user_data["wojsko"][self.unit_name] -= 1
            save_data(users)

        await self.view.update_embed(interaction)


@bot.command()
@commands.has_permissions(administrator=True)
async def awoj(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("Musisz oznaczyć osobę.")
        return

    user_id = str(member.id)
    init_user(user_id)

    user_data = users[user_id]
    wojsko = user_data["wojsko"]
    status = "\n".join(f"{unit}: {count}" for unit, count in wojsko.items()
                       if count > 0)
    if not status:
        status = "Nie posiadasz żadnych jednostek."

    embed = discord.Embed(title=f"Stan wojska użytkownika {member}",
                          description=status,
                          color=discord.Color.blue())

    view = ArmyView(user_id)
    await ctx.send(embed=embed, view=view)


class BadaniaView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        init_user(user_id)
        self.user_data = users[user_id]

        for tech, data in technologies.items():
            badanie = self.user_data["badania"].get(tech,
                                                    {"status": "not started"})
            status = badanie["status"]

            # Możliwość startu:
            can_start = False
            if status == "not started":
                if all(self.user_data["badania"].get(req, {}).get("status") ==
                       "done" for req in data["requires"]):
                    if "year_required" in data and current_rp_year < data[
                            "year_required"]:
                        can_start = False
                    else:
                        can_start = True
            elif status == "in progress":
                can_start = True

            # Kolor i disabled:
            if status == "done":
                style = discord.ButtonStyle.secondary
                disabled = True
            elif status == "in progress":
                style = discord.ButtonStyle.primary
                disabled = False
            elif can_start:
                style = discord.ButtonStyle.green
                disabled = False
            else:
                style = discord.ButtonStyle.gray
                disabled = True

            self.add_item(
                BadanieButton(tech, user_id, self.user_data, status, can_start,
                              style, disabled))


class BadanieButton(discord.ui.Button):

    def __init__(self, tech_name, user_id, user_data, status, can_start, style,
                 disabled):
        super().__init__(label=f"{tech_name} ({status})",
                         style=style,
                         disabled=disabled)
        self.tech_name = tech_name
        self.user_id = user_id
        self.user_data = user_data
        self.status = status
        self.can_start = can_start

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message(
                "Nie możesz zarządzać czyimiś badaniami.", ephemeral=True)
            return

        today = datetime.utcnow().date()
        last_date = self.user_data.get("last_badanie_date")

        if self.status == "in progress":
            # Sprawdź czy badanie się zakończyło
            badanie_info = self.user_data["badania"][self.tech_name]
            if badanie_info["end_date"] and today >= badanie_info["end_date"]:
                # Zakończ badanie
                self.user_data["badania"][self.tech_name]["status"] = "done"
                self.user_data["badania"][self.tech_name]["start_date"] = None
                self.user_data["badania"][self.tech_name]["end_date"] = None
                await interaction.response.send_message(
                    f"Badania nad {self.tech_name} zostały zakończone! {interaction.user.mention}",
                    ephemeral=False)
                self.user_data["last_badanie_date"] = today
                # Odśwież widok
                view = BadaniaView(self.user_id)
                await interaction.message.edit(view=view)
                return
            else:
                # Jeszcze trwa badanie
                dni = (badanie_info["end_date"] -
                       today).days if badanie_info["end_date"] else "??"
                await interaction.response.send_message(
                    f"Badania nad {self.tech_name} trwają jeszcze. Pozostało dni: {dni}",
                    ephemeral=True)
                return

        if self.status == "done":
            await interaction.response.send_message(
                f"Badania nad {self.tech_name} już zakończone.",
                ephemeral=True)
            return

        if self.status == "not started":
            # Sprawdź czy już badanie dzisiaj było
            if last_date == today:
                await interaction.response.send_message(
                    "Możesz rozpocząć tylko jedno badanie dziennie.",
                    ephemeral=True)
                return
            # Rozpocznij badanie
            days_needed = technologies[self.tech_name]["days"]
            start_date = today
            end_date = start_date + timedelta(
                days=days_needed) if days_needed > 0 else start_date

            self.user_data["badania"][self.tech_name] = {
                "status": "in progress",
                "start_date": start_date,
                "end_date": end_date,
            }
            self.user_data["last_badanie_date"] = today
            await interaction.response.send_message(
                f"Rozpoczęto badania nad {self.tech_name}. Potrwają do {end_date}.",
                ephemeral=True)
            view = BadaniaView(self.user_id)
            await interaction.message.edit(view=view)


@bot.command()
async def badania(ctx):
    user_id = str(ctx.author.id)
    init_user(user_id)
    embed = Embed(
        title="Drzewko technologiczne",
        description=
        "* - badanie dostępne od startu\nNumer przy badaniu to liczba dni potrzebna na badanie.",
        color=discord.Color.blue())

    # Generujemy opis drzewka
    lines = []
    for tech, data in technologies.items():
        prefix = "*" if data.get("start") else f"{data.get('days', '?')}d"
        lines.append(f"{tech} {prefix}")
    embed.add_field(name="Technologie", value="\n".join(lines), inline=False)

    view = BadaniaView(user_id)
    await ctx.send(embed=embed, view=view)


def set_alliance_members_relations(alliance_id):
    members = alliances[alliance_id]["members"]
    for i, uid1 in enumerate(members):
        for uid2 in members[i + 1:]:
            key = f"{min(uid1, uid2)}_{max(uid1, uid2)}"
            if "relacje" not in users[uid1]:
                users[uid1]["relacje"] = {}
            if "relacje" not in users[uid2]:
                users[uid2]["relacje"] = {}
            users[uid1]["relacje"][key] = 100
            users[uid2]["relacje"][key] = 100
    save_data(users)
    print("Relacje po ustawieniu:",
          {uid: users[uid]["relacje"]
           for uid in members})


class AdminBadaniaView(discord.ui.View):

    def __init__(self, user_id: str):
        super().__init__()  # Poprawne wywołanie konstruktora rodzica
        self.user_id = user_id
        init_user(user_id)
        self.user_data = users[user_id]
        for tech in technologies:
            status = self.user_data["badania"].get(
                tech, {"status": "not started"})["status"]
            button = AdminBadanieButton(tech, user_id, self.user_data, status)
            self.add_item(button)


class AdminBadanieButton(discord.ui.Button):

    def __init__(self, tech_name, user_id, user_data, status):
        label = f"{tech_name} ({status})"
        style = discord.ButtonStyle.gray
        if status == "done":
            style = discord.ButtonStyle.green
        elif status == "in progress":
            style = discord.ButtonStyle.blurple
        elif status == "not started":
            style = discord.ButtonStyle.red
        super().__init__(label=label,
                         style=style)  # Poprawne wywołanie konstruktora
        self.tech_name = tech_name
        self.user_id = user_id
        self.user_data = user_data

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Nie masz uprawnień do tej akcji.", ephemeral=True)
            return
        # Logic to toggle status of the research
        current_status = self.user_data["badania"].get(
            self.tech_name, {"status": "not started"})["status"]
        today = datetime.utcnow().date()
        if current_status == "not started":
            days_needed = technologies[self.tech_name]["days"]
            start_date = today
            end_date = start_date + timedelta(
                days=days_needed) if days_needed > 0 else start_date
            self.user_data["badania"][self.tech_name] = {
                "status": "in progress",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            await interaction.response.send_message(
                f"Rozpoczęto badania nad {self.tech_name}. Potrwają do {end_date}.",
                ephemeral=True)
        elif current_status == "in progress":
            self.user_data["badania"][self.tech_name]["status"] = "done"
            self.user_data["badania"][self.tech_name]["start_date"] = None
            self.user_data["badania"][self.tech_name]["end_date"] = None
            await interaction.response.send_message(
                f"Badania nad {self.tech_name} zostały zakończone!",
                ephemeral=True)
        elif current_status == "done":
            self.user_data["badania"][self.tech_name] = {
                "status": "not started",
                "start_date": None,
                "end_date": None
            }
            await interaction.response.send_message(
                f"Badanie nad {self.tech_name} zostało zresetowane.",
                ephemeral=True)
        # Save changes to file
        save_data(users)
        # Refresh view
        view = AdminBadaniaView(self.user_id)
        await interaction.message.edit(view=view)

        await interaction.message.edit(view=view)


@bot.command()
@commands.has_permissions(administrator=True)
async def abadania(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("Musisz oznaczyć osobę.")
        return
    user_id = str(member.id)
    init_user(user_id)
    user_data = users[user_id]
    embed = discord.Embed(
        title=f"Badania użytkownika {member}",
        description=
        "Kliknij przycisk, aby zmienić status badania (not started -> in progress -> done -> reset).",
        color=discord.Color.blue())
    lines = []
    for tech, data in user_data["badania"].items():
        lines.append(f"{tech}: {data['status']}")
    embed.add_field(name="Status badań", value="\n".join(lines), inline=False)
    view = AdminBadaniaView(user_id)
    await ctx.send(embed=embed, view=view)


@bot.command()
async def kup_fabryke(ctx):
    if not has_role(ctx.author):
        await ctx.send(
            f"{ctx.author.mention}, nie masz wymaganej roli, aby korzystać z tej komendy."
        )
        return

    uid = str(ctx.author.id)
    init_user(uid)

    if users[uid]["punkty"] >= 5:
        users[uid]["punkty"] -= 5
        users[uid]["fabryki"] += 1
        save_data(users)
        await ctx.send(
            f"{ctx.author.mention}, kupiłeś fabrykę! Masz teraz {users[uid]['fabryki']} fabryk."
        )
    else:
        await ctx.send("Nie masz wystarczająco punktów (koszt: 5).")


@bot.command()
@commands.has_permissions(administrator=True)
async def adc(ctx,
              member: discord.Member,
              nazwa: str,
              wartosc: int,
              dni: int = None):
    uid = str(member.id)
    init_user(uid)

    if not has_role(member):
        await ctx.send(
            f"❌ Nie można nadać cechy, ponieważ {member.mention} nie ma wymaganej roli."
        )
        return

    if wartosc == 0:
        await ctx.send("⚠️ Wartość cechy nie może być zerowa.")
        return

    cecha = {
        "nazwa": nazwa,
        "wartosc": wartosc,
        "nadana": str(date.today()),
        "czas": dni  # None = bezterminowo
    }

    users[uid]["cechy"].append(cecha)
    save_data(users)

    znak = "+" if wartosc > 0 else "-"
    limit_info = f" na {dni} dni" if dni is not None else " bez limitu czasu"
    await ctx.send(
        f"✅ Nadano {member.mention} cechę **{nazwa}** ({znak}{abs(wartosc)} pkt dziennie){limit_info}."
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def adr(ctx, member: discord.Member, nazwa: str):
    uid = str(member.id)
    init_user(uid)

    cechy = users[uid].get("cechy", [])
    before = len(cechy)
    cechy = [c for c in cechy if c["nazwa"] != nazwa]
    after = len(cechy)
    users[uid]["cechy"] = cechy
    save_data(users)

    if before == after:
        await ctx.send(
            f"⚠️ Nie znaleziono cechy **{nazwa}** u {member.mention}.")
    else:
        await ctx.send(f"🧹 Usunięto cechę **{nazwa}** u {member.mention}.")


@bot.command()
async def bal(ctx, member: discord.Member = None):
    if not has_role(ctx.author):
        await ctx.send(
            f"{ctx.author.mention}, nie masz wymaganej roli, aby korzystać z tej komendy."
        )
        return

    if member is None:
        member = ctx.author
    uid = str(member.id)
    init_user(uid)
    punkty = users[uid]["punkty"]
    await ctx.send(f"{member.display_name} ma {punkty} punktów.")


@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if not has_role(ctx.author):
        await ctx.send(
            f"{ctx.author.mention}, nie masz wymaganej roli, aby korzystać z tej komendy."
        )
        return

    if not has_role(member):
        await ctx.send(
            "Użytkownik, któremu chcesz przelać punkty, nie ma wymaganej roli."
        )
        return

    if member == ctx.author:
        await ctx.send("Nie możesz przelać punktów samemu sobie!")
        return

    sender = str(ctx.author.id)
    receiver = str(member.id)
    init_user(sender)
    init_user(receiver)

    if amount <= 0:
        await ctx.send("Wprowadź liczbę większą niż 0.")
        return

    if users[sender]["punkty"] >= amount:
        users[sender]["punkty"] -= amount
        users[receiver]["punkty"] += amount
        save_data(users)
        await ctx.send(
            f"{ctx.author.mention} przelał {amount} punktów do {member.mention}."
        )
    else:
        await ctx.send("Nie masz tyle punktów.")


@bot.command()
@commands.has_permissions(administrator=True)
async def addpoints(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("Wprowadź wartość większą niż 0.")
        return
    uid = str(member.id)
    init_user(uid)
    users[uid]["punkty"] += amount
    save_data(users)
    await ctx.send(
        f"Dodano {amount} punktów użytkownikowi {member.mention}. Teraz ma {users[uid]['punkty']} punktów."
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def removepoints(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("Wprowadź wartość większą niż 0.")
        return
    uid = str(member.id)
    init_user(uid)
    if users[uid]["punkty"] < amount:
        users[uid]["punkty"] = 0
    else:
        users[uid]["punkty"] -= amount
    save_data(users)
    await ctx.send(
        f"Usunięto {amount} punktów od użytkownika {member.mention}. Teraz ma {users[uid]['punkty']} punktów."
    )


@addpoints.error
@removepoints.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Nie masz uprawnień do użycia tej komendy.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(
            "Niepoprawne argumenty. Użycie: !addpoints @użytkownik liczba")
    else:
        raise error


class SpyPanel(View):

    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = str(user_id)

    @discord.ui.button(label="Kup szpiega (30 punktów)",
                       style=discord.ButtonStyle.green)
    async def buy_spy(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
        user = users.get(self.user_id)
        if user is None:
            await interaction.response.send_message(
                "Nie znaleziono użytkownika.", ephemeral=True)
            return

        if user["punkty"] < 30:
            await interaction.response.send_message(
                "Nie masz wystarczająco punktów!", ephemeral=True)
            return

        user["punkty"] -= 30
        user["szpiedzy"] = user.get("szpiedzy", 0) + 1
        save_data(users)

        # Nowy embed z aktualnymi danymi
        new_embed = discord.Embed(
            title=f"🔎 Panel wywiadu — {interaction.user.display_name}",
            description=
            f"Masz **{user['szpiedzy']}** szpiegów.\nPozostało punktów: {user['punkty']}",
            color=discord.Color.green())

        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="Użyj szpiega", style=discord.ButtonStyle.blurple)
    async def use_spy(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
        user = users.get(self.user_id)
        if user is None:
            await interaction.response.send_message(
                "Nie znaleziono użytkownika.", ephemeral=True)
            return

        if user.get("szpiedzy", 0) < 1:
            await interaction.response.send_message(
                "Nie masz szpiegów do użycia!", ephemeral=True)
            return

        user["szpiedzy"] -= 1
        save_data(users)

        role_id = 1390273080546562068
        role = interaction.guild.get_role(role_id)
        if role is None:
            await interaction.response.send_message(
                "Nie znaleziono roli do pingowania.", ephemeral=True)
            return

        new_embed = discord.Embed(
            title=f"🔎 Panel wywiadu — {interaction.user.display_name}",
            description=f"Pozostało szpiegów: **{user['szpiedzy']}**",
            color=discord.Color.green())

        await interaction.response.edit_message(embed=new_embed, view=self)

        await interaction.followup.send(
            f"{role.mention}, szpieg został użyty przez {interaction.user.mention}!"
        )


@bot.command()
async def wywiad(ctx):
    uid = str(ctx.author.id)
    init_user(uid)  # Upewniamy się, że user istnieje

    user = users[uid]
    szpiedzy = user.get("szpiedzy", 0)

    embed = discord.Embed(title=f"🔎 Panel wywiadu — {ctx.author.display_name}",
                          description=f"Masz **{szpiedzy}** szpiegów.",
                          color=discord.Color.green())

    view = SpyPanel(uid)
    await ctx.send(embed=embed, view=view)


@bot.command()
async def info(ctx, member: discord.Member = None):
    member = member or ctx.author
    uid = str(member.id)

    if not has_role(member):
        await ctx.send(
            f"❌ {member.mention} nie posiada wymaganej roli, by korzystać z systemu."
        )
        return

    init_user(uid)
    user = users[uid]

    embed = discord.Embed(title=f"📊 Panel gracza: {member.display_name}",
                          color=discord.Color.blue())

    embed.add_field(name="💰 Punkty",
                    value=f"**{user['punkty']}**",
                    inline=False)

    # Cechy
    if user["cechy"]:
        cechy_text = ""
        for cecha in user["cechy"]:
            nazwa = cecha["nazwa"]
            wartosc = cecha["wartosc"]
            czas = cecha["czas"]
            if czas is None:
                czas_txt = "🔁 Bez limitu"
            else:
                czas_txt = f"📆 {czas} dni"
            cechy_text += f"• **{nazwa}** ({wartosc:+d}/dzień, {czas_txt})\n"
    else:
        cechy_text = "Brak cech"

    embed.add_field(name="🧬 Cechy", value=cechy_text, inline=False)

    # Fabryki
    embed.add_field(name="🏭 Liczba fabryk",
                    value=f"**{user['fabryki']}**",
                    inline=False)

    sila_lad = 0
    for unit_name, count in user["wojsko"].items():
        if unit_name in units_land:
            sila = units.get(unit_name, 0) // 2
            sila_lad += sila * count

    # Obliczamy siłę jednostek morskich (połowa ceny)
    sila_morska = 0
    for unit_name, count in user["wojsko"].items():
        if unit_name in units_sea:
            sila = units.get(unit_name, 0) // 3
            sila_morska += sila * count

    # Obliczamy siłę jednostek lotniczych (sterowce * 4)
    sila_lot = 0
    for unit_name, count in user["wojsko"].items():
        if unit_name in units_air:
            sila_lot += count * 4

    # Dodajemy pola do embeda
    embed.add_field(name="⚔️ Siła jednostek lądowych",
                    value=f"**{sila_lad}**",
                    inline=False)

    embed.add_field(name="🚢 Siła jednostek morskich",
                    value=f"**{sila_morska}**",
                    inline=False)

    embed.add_field(name="✈️ Siła jednostek lotniczych",
                    value=f"**{sila_lot}**",
                    inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def leaderboard(ctx):
    role_id = 1389959233461682256  # ID roli, według której filtrujemy

    if not users:
        await ctx.send("Brak danych.")
        return

    role = ctx.guild.get_role(role_id)
    if role is None:
        await ctx.send("Nie znaleziono roli o podanym ID.")
        return

    user_items = []
    for uid, data in users.items():
        if isinstance(data, dict) and "punkty" in data:
            member = ctx.guild.get_member(int(uid))
            if member and role in member.roles:
                user_items.append((uid, data))

    if not user_items:
        await ctx.send("Brak użytkowników z wymaganą rolą i danymi o punktach."
                       )
        return

    def get_name(uid):
        member = ctx.guild.get_member(int(uid))
        if member:
            name = member.display_name
            return name if len(name) <= 19 else name[:18] + "…"
        return f"Użytkownik {uid}"

    # --- Definicje jednostek ---
    units_land = {
        "Piechota liniowa", "Kawaleria lekka", "Kawaleria ciężka",
        "Piechota ciężka", "Lekkie działo", "Czołg lekki", "Ciężkie działo",
        "Czołg średni", "Czołg ciężki"
    }
    units_sea = {
        "Statek transportowy", "Krążownik", "Niszczyciel", "Pancernik"
    }
    units_air = {"Sterowiec bombowy"}

    # --- Ranking punktów ---
    top_points = sorted(user_items, key=lambda x: x[1]["punkty"],
                        reverse=True)[:10]
    embed_points = discord.Embed(title="🏆 Top 10 państw — Punkty",
                                 color=discord.Color.gold())
    for i, (uid, data) in enumerate(top_points, start=1):
        embed_points.add_field(name=f"{i}. {get_name(uid)}",
                               value=f"Punkty: **{data['punkty']}**",
                               inline=False)

    # --- Ranking fabryk ---
    top_factories = sorted(user_items,
                           key=lambda x: x[1]["fabryki"],
                           reverse=True)[:10]
    embed_factories = discord.Embed(title="🏭 Top 10 państw — Fabryki",
                                    color=discord.Color.dark_orange())
    for i, (uid, data) in enumerate(top_factories, start=1):
        embed_factories.add_field(name=f"{i}. {get_name(uid)}",
                                  value=f"Fabryki: **{data['fabryki']}**",
                                  inline=False)

    # --- Ranking siły lądowej ---
    top_land = []
    for uid, data in user_items:
        wojsko = data.get("wojsko", {})
        sila_ladowa = 0
        for unit_name, count in wojsko.items():
            if unit_name in units_land:
                sila = units.get(unit_name, 0) // 2
                sila_ladowa += sila * count
        top_land.append((uid, sila_ladowa))
    top_land.sort(key=lambda x: x[1], reverse=True)
    top_land = top_land[:10]

    embed_land = discord.Embed(
        title="⚔️ Top 10 państw — Siła jednostek lądowych",
        color=discord.Color.red())
    for i, (uid, sila) in enumerate(top_land, start=1):
        embed_land.add_field(name=f"{i}. {get_name(uid)}",
                             value=f"Siła: **{sila}**",
                             inline=False)

    # --- Ranking siły morskiej ---
    top_sea = []
    for uid, data in user_items:
        wojsko = data.get("wojsko", {})
        sila_morska = 0
        for unit_name, count in wojsko.items():
            if unit_name in units_sea:
                sila = units.get(unit_name, 0) // 2
                sila_morska += sila * count
        top_sea.append((uid, sila_morska))
    top_sea.sort(key=lambda x: x[1], reverse=True)
    top_sea = top_sea[:10]

    embed_sea = discord.Embed(
        title="🚢 Top 10 państw — Siła jednostek morskich",
        color=discord.Color.blue())
    for i, (uid, sila) in enumerate(top_sea, start=1):
        embed_sea.add_field(name=f"{i}. {get_name(uid)}",
                            value=f"Siła: **{sila}**",
                            inline=False)

    # --- Ranking siły powietrznej ---
    top_air = []
    for uid, data in user_items:
        wojsko = data.get("wojsko", {})
        count_sterowce = wojsko.get("Sterowiec bombowy", 0)
        sila_powietrzna = count_sterowce * 4
        top_air.append((uid, sila_powietrzna))
    top_air.sort(key=lambda x: x[1], reverse=True)
    top_air = top_air[:10]

    embed_air = discord.Embed(
        title="✈️ Top 10 państw — Siła jednostek powietrznych",
        color=discord.Color.green())
    for i, (uid, sila) in enumerate(top_air, start=1):
        embed_air.add_field(name=f"{i}. {get_name(uid)}",
                            value=f"Siła: **{sila}**",
                            inline=False)

    # Wysyłamy embedy
    await ctx.send(embed=embed_points)
    await ctx.send(embed=embed_factories)
    await ctx.send(embed=embed_land)
    await ctx.send(embed=embed_sea)
    await ctx.send(embed=embed_air)


@bot.command()
async def relacje(ctx,
                  member1: discord.Member = None,
                  member2: discord.Member = None):
    role_id = 1389959233461682256

    # Jeśli podano dwie osoby, to ich używamy, jeśli jedną, to druga to autor, jeśli żadnej - błąd
    if member1 and member2:
        uid1, uid2 = str(member1.id), str(member2.id)
        m1, m2 = member1, member2
    elif member1:
        uid1, uid2 = str(ctx.author.id), str(member1.id)
        m1, m2 = ctx.author, member1
    else:
        await ctx.send("Podaj przynajmniej jedną osobę.")
        return

    # Sprawdzamy role
    if not any(role.id == role_id for role in m1.roles):
        await ctx.send(
            f"{m1.mention} nie ma wymaganej roli do wyświetlenia relacji.")
        return

    if not any(role.id == role_id for role in m2.roles):
        await ctx.send(
            f"{m2.mention} nie ma wymaganej roli do wyświetlenia relacji.")
        return

    uid1 = str(m1.id)
    uid2 = str(m2.id)

    init_user(uid1)
    init_user(uid2)

    key = tuple(sorted([uid1, uid2]))
    rel = users.get("relacje", {}).get(f"{key[0]}_{key[1]}", 0)

    rel_text = f"+{rel}" if rel > 0 else str(rel)

    color = discord.Color.green() if rel > 0 else discord.Color.red(
    ) if rel < 0 else discord.Color.light_grey()

    name1 = m1.display_name
    name2 = m2.display_name

    embed = discord.Embed(title="🤝 Relacja",
                          description=f"{name1} ↔ {name2}\n**{rel_text}**",
                          color=color)

    await ctx.send(embed=embed)


@bot.command()
async def urel(ctx, member: discord.Member, value: int):
    if not has_role(ctx.author):
        await ctx.send(
            f"{ctx.author.mention}, nie masz wymaganej roli, aby korzystać z tej komendy."
        )
        return
    if member == ctx.author:
        await ctx.send("Nie możesz ustawić relacji z samym sobą.")
        return

        # Sprawdzenie czy obaj są w tym samym sojuszu
    uid1 = str(ctx.author.id)
    uid2 = str(member.id)
    init_user(uid1)
    init_user(uid2)

    if value < -100 or value > 100:
        await ctx.send("Wartość relacji musi być w zakresie od -100 do 100.")
        return

    key = f"{min(uid1, uid2)}_{max(uid1, uid2)}"
    users["relacje"][key] = value
    save_data(users)
    await ctx.send(
        f"Zmieniono relację między {ctx.author.display_name} a {member.display_name} na **{value}**."
    )


@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="📖 Pomoc — Komendy Gracza",
                          color=discord.Color.blue())
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    embed.add_field(name="!rp_year",
                    value="📅 Sprawdź obecny rok RP.",
                    inline=False)
    embed.add_field(name="!daily",
                    value="🎁 Odbierz codzienne punkty.",
                    inline=False)
    embed.add_field(name="!kup_fabryke",
                    value="🏭 Kup fabrykę za 5 punktów.",
                    inline=False)
    embed.add_field(name="!bal [@użytkownik]",
                    value="💰 Sprawdź punkty (domyślnie Twoje).",
                    inline=False)
    embed.add_field(name="!pay <@użytkownik> <ilość>",
                    value="🔁 Przelej punkty innemu graczowi.",
                    inline=False)
    embed.add_field(name="!info [@użytkownik]",
                    value="🧾 Szczegóły gracza (cechy, punkty, fabryki).",
                    inline=False)
    embed.add_field(name="!leaderboard",
                    value="📊 Top 10 graczy według punktów i fabryk.",
                    inline=False)
    embed.add_field(name="!relacje <@1> [@2]",
                    value="🤝 Sprawdź relację między graczami.",
                    inline=False)
    embed.add_field(name="!urel <@użytkownik> <wartość>",
                    value="⚖️ Ustaw relację z graczem (-100 do 100).",
                    inline=False)
    embed.add_field(name="!wojsko",
                    value="⚔️ Otwórz panel zarządzania wojskiem.",
                    inline=False)
    embed.add_field(
        name="!badania",
        value="🔬 Otwórz panel zarządzania badaniami technologicznymi.",
        inline=False)
    embed.add_field(name="!wywiad",
                    value="🔎 Otwórz panel wywiadu i zarządzaj szpiegami.",
                    inline=False)
    embed.add_field(name="!sojusz",
                    value="🤝 Otwórz panel sojuszu i zarządzaj swoim sojuszem.",
                    inline=False)
    embed.set_footer(
        text="Użyj !adm_help, aby zobaczyć komendy administratora.")
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def adm_help(ctx):
    embed = discord.Embed(title="🔧 Pomoc Administratora",
                          color=discord.Color.red())
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)

    embed.add_field(name="!addpoints <@użytkownik> <ilość>",
                    value="➕ Dodaj punkty.",
                    inline=False)
    embed.add_field(name="!removepoints <@użytkownik> <ilość>",
                    value="➖ Usuń punkty.",
                    inline=False)
    embed.add_field(name="!adc <@użytkownik> <nazwa> <wartość> [dni]",
                    value="🧬 Nadaj cechę użytkownikowi.",
                    inline=False)
    embed.add_field(name="!adr <@użytkownik> <nazwa>",
                    value="🧹 Usuń cechę użytkownika.",
                    inline=False)

    embed.set_footer(text="Tylko administratorzy mogą używać tych komend.")
    await ctx.send(embed=embed)


def get_user_alliance(uid):
    init_user(uid)
    return users[uid]["alliance_id"]


def get_alliance_members(alliance_id):
    return alliances.get(alliance_id, {}).get("members", [])


def is_owner(uid, alliance_id):
    return alliances.get(alliance_id, {}).get("owner") == uid


def get_user_alliance_id(user_id):
    user = users.get(str(user_id))
    if not user:
        return None
    alliance_id = user.get("alliance_id")
    if alliance_id not in alliances:
        user["alliance_id"] = None  # <- automatyczne czyszczenie
        return None
    return alliance_id


def is_admin_or_owner(user_id, alliance_id):
    alliance = alliances.get(alliance_id)
    if not alliance:
        return False
    if alliance["owner"] == user_id:
        return True
    if "admins" in alliance and user_id in alliance["admins"]:
        return True
    return False


async def approve_join_request(user_id: str, alliance_id: str,
                               interaction: discord.Interaction):
    alliance = alliances.get(alliance_id)
    if not alliance:
        await interaction.response.send_message("Sojusz nie istnieje.",
                                                ephemeral=True)
        return

    if user_id in alliance["members"]:
        await interaction.response.send_message(
            "Użytkownik już jest w sojuszu.", ephemeral=True)
        return

    alliance["members"].append(user_id)
    users[user_id]["alliance_id"] = alliance_id

    set_alliance_members_relations(
        alliance_id)  # ustaw relacje 100 między wszystkimi członkami

    save_data(users)
    save_alliances(alliances)

    await interaction.response.send_message(
        f"Użytkownik <@{user_id}> został dodany do sojuszu **{alliance['name']}**.",
        ephemeral=True)


# --- Views i przyciski ---


class AllianceMainPanel(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.alliance_id = get_user_alliance(user_id) or None

    @discord.ui.button(label="Załóż nowy sojusz",
                       style=discord.ButtonStyle.green)
    async def create_alliance(self, interaction: discord.Interaction,
                              button: discord.ui.Button):
        if get_user_alliance_id(self.user_id):
            await interaction.response.send_message("Jesteś już w sojuszu!",
                                                    ephemeral=True)
            return

        await interaction.response.send_modal(
            CreateAllianceModal(self.user_id, self))

    @discord.ui.button(label="Lista sojuszy",
                       style=discord.ButtonStyle.blurple)
    async def list_alliances(self, interaction: discord.Interaction,
                             button: discord.ui.Button):
        embed = discord.Embed(title="Lista sojuszy",
                              color=discord.Color.blue())
        if not alliances:
            embed.description = "Brak sojuszy."
        else:
            for aid, data in alliances.items():
                embed.add_field(name=data["name"],
                                value=f"Członków: {len(data['members'])}",
                                inline=False)

        await interaction.response.edit_message(embed=embed,
                                                view=AllianceJoinView(
                                                    self.user_id))

    @discord.ui.button(label="Panel sojuszu", style=discord.ButtonStyle.gray)
    async def manage_alliance(self, interaction: discord.Interaction,
                              button: discord.ui.Button):
        alliance_id = get_user_alliance_id(self.user_id)
        if not alliance_id:
            await interaction.response.send_message(
                "Nie jesteś w żadnym sojuszu.", ephemeral=True)
            return

        await interaction.response.edit_message(
            embed=alliance_embed(alliance_id),
            view=AllianceManageView(self.user_id, alliance_id))


class CreateAllianceModal(discord.ui.Modal, title="Załóż nowy sojusz"):

    def __init__(self, user_id, parent_view):
        super().__init__()
        self.user_id = user_id
        self.parent_view = parent_view
        self.name = discord.ui.TextInput(label="Nazwa sojuszu",
                                         min_length=3,
                                         max_length=30)

        self.add_item(self.name)

    async def on_submit(self, interaction: discord.Interaction):
        if get_user_alliance_id(self.user_id):
            await interaction.response.send_message("Jesteś już w sojuszu!",
                                                    ephemeral=True)
            return

        # Tworzymy nowy sojusz
        new_id = str(uuid.uuid4())[:8]
        alliances[new_id] = {
            "name": self.name.value,
            "owner": self.user_id,
            "members": [self.user_id],
            "invitations": []
        }
        users[self.user_id]["alliance_id"] = new_id
        save_data(users)
        save_alliances(alliances)
        set_alliance_members_relations(new_id)

        await interaction.response.send_message(
            f"Założono sojusz **{self.name.value}**!", ephemeral=True)
        # Odśwież panel
        await interaction.message.edit(embed=alliance_embed(new_id),
                                       view=AllianceManageView(
                                           self.user_id, new_id))


class AllianceJoinView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.page = 0
        self.per_page = 5
        self.alliance_ids = list(alliances.keys())
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.page * self.per_page
        end = start + self.per_page
        page_alliances = self.alliance_ids[start:end]

        for aid in page_alliances:
            name = alliances[aid]["name"]
            btn = discord.ui.Button(label=f"Dołącz: {name}",
                                    style=discord.ButtonStyle.green)
            btn.callback = self.make_join_request_callback(aid)
            self.add_item(btn)

        # Przycisk poprzednia strona
        prev_btn = discord.ui.Button(label="◀️",
                                     style=discord.ButtonStyle.gray,
                                     disabled=self.page == 0)
        prev_btn.callback = self.prev_page
        self.add_item(prev_btn)

        # Przycisk następna strona
        next_btn = discord.ui.Button(label="▶️",
                                     style=discord.ButtonStyle.gray,
                                     disabled=end >= len(self.alliance_ids))
        next_btn.callback = self.next_page
        self.add_item(next_btn)

        # Przycisk powrotu
        back_btn = discord.ui.Button(label="Powrót",
                                     style=discord.ButtonStyle.red)
        back_btn.callback = self.go_back
        self.add_item(back_btn)

    def make_join_request_callback(self, alliance_id):

        async def callback(interaction: discord.Interaction):
            if get_user_alliance_id(self.user_id):
                await interaction.response.send_message(
                    "Jesteś już w sojuszu!", ephemeral=True)
                return

            owner_id = alliances[alliance_id][
                "owner"]  # poprawione z owner_id na owner

            # Dodanie prośby o dołączenie do listy oczekujących
            if alliance_id not in pending_join_requests:
                pending_join_requests[alliance_id] = set()
            pending_join_requests[alliance_id].add(self.user_id)

            # Wysłanie wiadomości prywatnej do właściciela sojuszu z przyciskami
            try:
                owner_user = await interaction.client.fetch_user(int(owner_id))
                view = JoinRequestApprovalView(alliance_id, self.user_id,
                                               owner_id)
                await owner_user.send(
                    f"Użytkownik <@{self.user_id}> chce dołączyć do sojuszu **{alliances[alliance_id]['name']}**.\n"
                    f"Zatwierdź lub odrzuć prośbę klikając poniższe przyciski.",
                    view=view)
            except Exception as e:
                print(
                    f"Nie udało się wysłać wiadomości do właściciela sojuszu: {e}"
                )

            await interaction.response.send_message(
                f"Wysłano prośbę o dołączenie do sojuszu **{alliances[alliance_id]['name']}**. Czekaj na zatwierdzenie.",
                ephemeral=True)

        return callback

    async def prev_page(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        if (self.page + 1) * self.per_page < len(self.alliance_ids):
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(view=self)

    async def go_back(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=main_embed(self.user_id),
                                                view=AllianceMainPanel(
                                                    self.user_id))


class AllianceManageView(discord.ui.View):

    def __init__(self, user_id, alliance_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.alliance_id = alliance_id

        # Dodajemy przyciski do zarządzania
        self.add_item(InviteMemberButton(user_id, alliance_id))
        self.add_item(RemoveMemberButton(user_id, alliance_id))
        self.add_item(ChangeNameButton(user_id, alliance_id))
        self.add_item(DissolveAllianceButton(user_id, alliance_id))
        self.add_item(LeaveAllianceButton(user_id, alliance_id))


from discord.ui import Select, View
from discord import SelectOption


class InviteMemberSelect(Select):

    def __init__(self, alliance_id, members):
        options = [
            SelectOption(label=m.display_name, value=str(m.id))
            for m in members[:25]
        ]
        super().__init__(placeholder="Wybierz członka do zaproszenia...",
                         options=options)
        self.alliance_id = alliance_id

    async def callback(self, interaction: discord.Interaction):
        invite_uid = self.values[0]
        if invite_uid not in users:
            await interaction.response.send_message(
                "Użytkownik nie istnieje w systemie.", ephemeral=True)
            return

        alliance = alliances.get(self.alliance_id)
        if not alliance:
            await interaction.response.send_message("Sojusz nie istnieje.",
                                                    ephemeral=True)
            return

        if invite_uid in alliance["members"]:
            await interaction.response.send_message(
                "Użytkownik już jest w sojuszu.", ephemeral=True)
            return

        if invite_uid in alliance["invitations"]:
            await interaction.response.send_message(
                "Użytkownik już ma zaproszenie.", ephemeral=True)
            return

        alliance["invitations"].append(invite_uid)
        save_alliances(alliances)

        # Wysyłamy DM do zaproszonego z przyciskami
        try:
            user = await interaction.client.fetch_user(int(invite_uid))
            await user.send(
                f"Zostałeś zaproszony do sojuszu **{alliance['name']}**.",
                view=InvitationResponseView(invite_uid, self.alliance_id))
        except Exception as e:
            await interaction.response.send_message(
                f"Nie udało się wysłać wiadomości do użytkownika: {e}",
                ephemeral=True)
            return

        await interaction.response.send_message(
            f"Zaproszenie wysłano do <@{invite_uid}>.", ephemeral=True)


class InviteMemberView(View):

    def __init__(self, user_id, alliance_id, guild):
        super().__init__(timeout=60)
        if not is_owner(user_id, alliance_id):
            return
        # filtrujemy użytkowników (np. którzy nie są w sojuszu)
        alliance = alliances.get(alliance_id)
        members_in_alliance = alliance["members"] if alliance else []
        candidates = [
            m for m in guild.members
            if not m.bot and str(m.id) not in members_in_alliance
        ]

        self.add_item(InviteMemberSelect(alliance_id, candidates))


class RemoveMemberView(View):

    def __init__(self, user_id, alliance_id, guild):
        super().__init__(timeout=60)
        if not is_owner(user_id, alliance_id):
            return
        alliance = alliances.get(alliance_id)
        if not alliance:
            return
        members_in_alliance = [
            guild.get_member(int(uid)) for uid in alliance["members"]
            if guild.get_member(int(uid)) is not None
        ]

        self.add_item(RemoveMemberSelect(alliance_id, members_in_alliance))


class InviteMemberButton(discord.ui.Button):

    def __init__(self, user_id, alliance_id):
        super().__init__(label="Zaproś członka",
                         style=discord.ButtonStyle.green)
        self.user_id = user_id
        self.alliance_id = alliance_id

    async def callback(self, interaction: discord.Interaction):
        if not is_admin_or_owner(str(interaction.user.id), self.alliance_id):
            await interaction.response.send_message(
                "Tylko właściciel lub admini mogą to robić!", ephemeral=True)
            return
        view = InviteMemberView(self.user_id, self.alliance_id,
                                interaction.guild)
        await interaction.response.send_message(
            "Wybierz użytkownika do zaproszenia:", view=view, ephemeral=True)


class RemoveMemberButton(discord.ui.Button):

    def __init__(self, user_id, alliance_id):
        super().__init__(label="Wyrzuć członka", style=discord.ButtonStyle.red)
        self.user_id = user_id
        self.alliance_id = alliance_id

    async def callback(self, interaction: discord.Interaction):
        if not is_admin_or_owner(str(interaction.user.id), self.alliance_id):
            await interaction.response.send_message(
                "Tylko właściciel lub admini mogą to robić!", ephemeral=True)
            return
        view = RemoveMemberView(self.user_id, self.alliance_id,
                                interaction.guild)
        await interaction.response.send_message(
            "Wybierz użytkownika do wyrzucenia:", view=view, ephemeral=True)


class ChangeNameButton(discord.ui.Button):

    def __init__(self, user_id, alliance_id):
        super().__init__(label="Zmień nazwę sojuszu",
                         style=discord.ButtonStyle.blurple)
        self.user_id = user_id
        self.alliance_id = alliance_id

    async def callback(self, interaction: discord.Interaction):
        if not is_admin_or_owner(str(interaction.user.id), self.alliance_id):
            await interaction.response.send_message(
                "Tylko właściciel lub admini mogą to robić!", ephemeral=True)
            return
        modal = ChangeNameModal(self.alliance_id, self.user_id)
        await interaction.response.send_modal(modal)


class ChangeNameModal(discord.ui.Modal, title="Zmień nazwę sojuszu"):

    def __init__(self, alliance_id, user_id):
        super().__init__()
        self.alliance_id = alliance_id
        self.user_id = user_id  # dodaj user_id
        self.new_name = discord.ui.TextInput(label="Nowa nazwa sojuszu",
                                             min_length=3,
                                             max_length=30)
        self.add_item(self.new_name)

    async def on_submit(self, interaction: discord.Interaction):
        if self.alliance_id not in alliances:
            await interaction.response.send_message("Sojusz nie istnieje.",
                                                    ephemeral=True)
            return
        alliances[self.alliance_id]["name"] = self.new_name.value
        save_alliances(alliances)
        await interaction.response.send_message(
            f"Nazwa sojuszu zmieniona na **{self.new_name.value}**.",
            ephemeral=True)
        await interaction.message.edit(embed=alliance_embed(self.alliance_id),
                                       view=AllianceManageView(
                                           self.user_id, self.alliance_id))


class LeaveAllianceButton(discord.ui.Button):

    def __init__(self, user_id, alliance_id):
        super().__init__(label="Opuść sojusz", style=discord.ButtonStyle.red)
        self.user_id = user_id
        self.alliance_id = alliance_id

    async def callback(self, interaction: discord.Interaction):
        alliance = alliances.get(self.alliance_id)
        if not alliance:
            await interaction.response.send_message("Sojusz nie istnieje.",
                                                    ephemeral=True)
            return

        # Jeśli użytkownik jest właścicielem – blokuj
        if alliance["owner"] == self.user_id:
            await interaction.response.send_message(
                "Jesteś właścicielem. Musisz najpierw rozwiązać sojusz.",
                ephemeral=True)
            return

        # Usuń użytkownika z członków i zaktualizuj dane
        if self.user_id in alliance["members"]:
            alliance["members"].remove(self.user_id)
        users[self.user_id]["alliance_id"] = None
        save_data(users)
        save_alliances(alliances)

        await interaction.response.send_message("Opuściłeś sojusz.",
                                                ephemeral=True)
        await interaction.message.edit(embed=main_embed(self.user_id),
                                       view=AllianceMainPanel(self.user_id))


class DissolveAllianceButton(discord.ui.Button):

    def __init__(self, user_id, alliance_id):
        super().__init__(label="Rozwiąż sojusz", style=discord.ButtonStyle.red)
        self.user_id = user_id
        self.alliance_id = alliance_id

    async def callback(self, interaction: discord.Interaction):

        if not is_admin_or_owner(str(interaction.user.id), self.alliance_id):
            await interaction.response.send_message(
                "Tylko właściciel lub admini mogą to robić!", ephemeral=True)
            return

        # Usuwamy sojusz, usuwamy wszystkim członkom alliance_id
        for uid in alliances[self.alliance_id]["members"]:
            if uid in users:
                users[uid]["alliance_id"] = None
            else:
                print(f"UWAGA! Użytkownik o ID {uid} nie istnieje w users!")
        del alliances[self.alliance_id]
        save_data(alliances)

        await interaction.response.send_message("Sojusz został rozwiązany.",
                                                ephemeral=True)
        # Odśwież panel użytkownika
        await interaction.message.edit(embed=main_embed(self.user_id),
                                       view=AllianceMainPanel(self.user_id))


class InvitationResponseView(discord.ui.View):

    def __init__(self, invitee_id, alliance_id):
        super().__init__(timeout=None)
        self.invitee_id = invitee_id
        self.alliance_id = alliance_id

    @discord.ui.button(label="Akceptuj", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
        if str(interaction.user.id) != self.invitee_id:
            await interaction.response.send_message(
                "To zaproszenie nie jest dla Ciebie.", ephemeral=True)
            return

        alliance = alliances.get(self.alliance_id)
        if not alliance:
            await interaction.response.send_message("Sojusz nie istnieje.",
                                                    ephemeral=True)
            return

        if self.invitee_id in alliance["members"]:
            await interaction.response.send_message(
                "Jesteś już w tym sojuszu.", ephemeral=True)
            return

        alliance["members"].append(self.invitee_id)
        set_alliance_members_relations(alliance_id)
        users[self.invitee_id]["alliance_id"] = self.alliance_id
        if self.invitee_id in alliance["invitations"]:
            alliance["invitations"].remove(self.invitee_id)

        save_data(users)
        save_alliances(alliances)

        await interaction.response.edit_message(
            content=f"Dołączyłeś do sojuszu **{alliance['name']}**!",
            view=None)

    @discord.ui.button(label="Odrzuć", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
        if str(interaction.user.id) != self.invitee_id:
            await interaction.response.send_message(
                "To zaproszenie nie jest dla Ciebie.", ephemeral=True)
            return

        alliance = alliances.get(self.alliance_id)
        if alliance and self.invitee_id in alliance["invitations"]:
            alliance["invitations"].remove(self.invitee_id)
            save_alliances(alliances)

        await interaction.response.edit_message(
            content="Odrzuciłeś zaproszenie.", view=None)


class RemoveMemberSelect(Select):

    def __init__(self, alliance_id, members):
        options = [
            SelectOption(label=m.display_name, value=str(m.id))
            for m in members[:25]
        ]
        super().__init__(placeholder="Wybierz członka do wyrzucenia...",
                         options=options)
        self.alliance_id = alliance_id

    async def callback(self, interaction: discord.Interaction):
        remove_uid = self.values[0]
        alliance = alliances.get(self.alliance_id)
        if not alliance:
            await interaction.response.send_message("Sojusz nie istnieje.",
                                                    ephemeral=True)
            return

        if remove_uid not in alliance["members"]:
            await interaction.response.send_message(
                "Użytkownik nie jest członkiem sojuszu.", ephemeral=True)
            return

        # Usuń użytkownika z sojuszu
        alliance["members"].remove(remove_uid)
        users[remove_uid]["alliance_id"] = None
        save_data(users)
        save_alliances(alliances)

        await interaction.response.send_message(
            f"Usunięto użytkownika <@{remove_uid}> z sojuszu.", ephemeral=True)

        # Odśwież widok zarządzania
        await interaction.message.edit(embed=alliance_embed(self.alliance_id),
                                       view=AllianceManageView(
                                           interaction.user.id,
                                           self.alliance_id))


class JoinRequestApprovalView(discord.ui.View):

    def __init__(self, alliance_id, requester_id, owner_id):
        super().__init__(timeout=None)
        self.alliance_id = alliance_id
        self.requester_id = requester_id
        self.owner_id = owner_id

    @discord.ui.button(label="Zatwierdź", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
        if interaction.user.id != int(self.owner_id):
            await interaction.response.send_message(
                "Tylko właściciel sojuszu może zatwierdzić prośbę.",
                ephemeral=True)
            return

        # Sprawdź, czy prośba dalej istnieje
        if self.alliance_id not in pending_join_requests or self.requester_id not in pending_join_requests[
                self.alliance_id]:
            await interaction.response.send_message(
                "Prośba już została rozpatrzona.", ephemeral=True)
            return

        # Dodaj użytkownika do członków sojuszu
        alliance = alliances.get(self.alliance_id)
        if not alliance:
            await interaction.response.send_message("Sojusz nie istnieje.",
                                                    ephemeral=True)
            return

        # Usuń prośbę z oczekujących
        pending_join_requests[self.alliance_id].remove(self.requester_id)
        set_alliance_members_relations(self.alliance_id)
        if not pending_join_requests[self.alliance_id]:
            del pending_join_requests[self.alliance_id]

        if self.requester_id not in alliance["members"]:
            alliance["members"].append(self.requester_id)
            users[self.requester_id]["alliance_id"] = self.alliance_id
            save_data(users)
            save_alliances(alliances)

            await interaction.response.edit_message(
                content=
                f"Użytkownik <@{self.requester_id}> został dodany do sojuszu **{alliance['name']}**.",
                view=None)
            try:
                user = await interaction.client.fetch_user(
                    int(self.requester_id))
                await user.send(
                    f"Twoja prośba o dołączenie do sojuszu **{alliance['name']}** została zatwierdzona!"
                )
            except:
                pass
        else:
            await interaction.response.edit_message(
                content="Użytkownik jest już członkiem sojuszu.", view=None)

    @discord.ui.button(label="Odrzuć", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
        if interaction.user.id != int(self.owner_id):
            await interaction.response.send_message(
                "Tylko właściciel sojuszu może odrzucić prośbę.",
                ephemeral=True)
            return

        if self.alliance_id not in pending_join_requests or self.requester_id not in pending_join_requests[
                self.alliance_id]:
            await interaction.response.send_message(
                "Prośba już została rozpatrzona.", ephemeral=True)
            return

        # Usuń prośbę z oczekujących
        pending_join_requests[self.alliance_id].remove(self.requester_id)
        if not pending_join_requests[self.alliance_id]:
            del pending_join_requests[self.alliance_id]

        await interaction.response.edit_message(
            content=
            f"Prośba użytkownika <@{self.requester_id}> została odrzucona.",
            view=None)
        try:
            user = await interaction.client.fetch_user(int(self.requester_id))
            await user.send(
                f"Twoja prośba o dołączenie do sojuszu **{alliances[self.alliance_id]['name']}** została odrzucona."
            )
        except:
            pass


# --- Pomocnicze embedy ---


def main_embed(user_id):
    alliance_id = get_user_alliance_id(
        user_id)  # <- upewnij się, że to bezpieczna wersja

    if not alliance_id:
        return discord.Embed(title="Brak sojuszu",
                             description="Nie jesteś w żadnym sojuszu.",
                             color=discord.Color.red())

    alliance = alliances[alliance_id]
    embed = discord.Embed(title=f"Twój sojusz: {alliance['name']}",
                          color=discord.Color.green())
    embed.add_field(name="Właściciel",
                    value=f"<@{alliance['owner']}>",
                    inline=False)
    members = "\n".join(f"<@{uid}>" for uid in alliance["members"]) or "Brak"
    embed.add_field(name="Członkowie", value=members, inline=False)

    return embed


def alliance_embed(alliance_id):
    if alliance_id not in alliances:
        embed = discord.Embed(
            title="Błąd",
            description="Sojusz nie istnieje lub został usunięty.",
            color=discord.Color.red())
        return embed

    alliance = alliances[alliance_id]
    embed = discord.Embed(title=f"Sojusz: {alliance['name']}",
                          color=discord.Color.green())
    embed.add_field(name="Właściciel",
                    value=f"<@{alliance['owner']}>",
                    inline=False)
    members_mention = "\n".join(f"<@{uid}>" for uid in alliance["members"])
    embed.add_field(name="Członkowie",
                    value=members_mention or "Brak członków",
                    inline=False)

    invited = alliance.get("invitations", [])
    if invited:
        invited_mention = "\n".join(f"<@{uid}>" for uid in invited)
        embed.add_field(name="Zaproszenia",
                        value=invited_mention,
                        inline=False)
    else:
        embed.add_field(name="Zaproszenia", value="Brak", inline=False)
    return embed


# --- Komenda !sojusz ---


@bot.command()
async def sojusz(ctx):
    uid = str(ctx.author.id)
    init_user(uid)

    view = AllianceMainPanel(uid)
    embed = main_embed(uid)

    await ctx.send(embed=embed, view=view)


@bot.command()
async def trel(ctx):
    role_id = 1389959233461682256
    guild = ctx.guild
    relacje = users.get("relacje", {})

    # Pobierz użytkowników z rolą
    members_with_role = [
        m for m in guild.members if any(r.id == role_id for r in m.roles)
    ]

    # Mapowanie ID do display_name (obcięte do 15 znaków)
    id_to_name = {
        str(m.id): (m.display_name[:14] +
                    "…" if len(m.display_name) > 15 else m.display_name)
        for m in members_with_role
    }

    if not id_to_name:
        await ctx.send(f"Brak użytkowników z rolą <@&{role_id}> na serwerze.")
        return

    # Bierzemy max 10 użytkowników dla czytelności
    filtered_user_ids = list(id_to_name.keys())[:10]

    embed = discord.Embed(
        title="📊 Tabela wzajemnych relacji",
        description=
        f"Relacje tylko między osobami z rolą <@&{role_id}>.\nSkala: -100 (wrogość) do 100 (przyjaźń).",
        color=discord.Color.blue())

    for uid_row in filtered_user_ids:
        row_name = id_to_name[uid_row]
        lines = []
        for uid_col in filtered_user_ids:
            if uid_row == uid_col:
                continue

            # Sprawdzamy, czy obie osoby mają rolę - już mamy, bo filtrujemy po id_to_name

            key = f"{min(uid_row, uid_col)}_{max(uid_row, uid_col)}"
            val = relacje.get(key, 0)

            if val > 50:
                emoji = "💚"
            elif val > 0:
                emoji = "🟢"
            elif val == 0:
                emoji = "⚪"
            elif val > -50:
                emoji = "🟠"
            else:
                emoji = "❤️‍🔥"

            col_name = id_to_name[uid_col]
            lines.append(f"{emoji} **{col_name}:** {val}")

        embed.add_field(name=row_name,
                        value="\n".join(lines) if lines else "Brak relacji",
                        inline=False)

    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    # Embed z czerwonym kolorem
    embed = discord.Embed(color=discord.Color.red())
    if isinstance(error, commands.CommandNotFound):
        embed.title = "Błąd"
        embed.description = "Niepoprawna komenda. Sprawdź dostępne komendy."
        await ctx.send(embed=embed)

    elif isinstance(error, commands.MissingRequiredArgument):
        embed.title = "Błąd"
        embed.description = f"Brakuje wymaganego argumentu: `{error.param.name}`."
        await ctx.send(embed=embed)

    else:
        # Inne błędy - możesz dodać obsługę lub ignorować
        embed.title = "Wystąpił błąd"
        embed.description = str(error)
        await ctx.send(embed=embed)


bot.run(os.getenv("TOKEN"))


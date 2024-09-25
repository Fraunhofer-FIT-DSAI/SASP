from enum import IntEnum
import random

class RandomNameGenerator:
    def __init__(self) -> None:
        self._ADJECTIVES = [
    "aback","abaft","abandoned","abashed","aberrant","abhorrent","abiding","abject","ablaze","able","abnormal","aboard","aboriginal","abortive","abounding","abrasive","abrupt","absent","absorbed","absorbing","abstracted","absurd","abundant","abusive","acceptable","accessible","accidental","accurate","acid","acidic","acoustic","acrid","actually","ad hoc","adamant","adaptable","addicted","adhesive","adjoining","adorable","adventurous","afraid","aggressive","agonizing","agreeable","ahead","ajar","alcoholic","alert","alike","alive","alleged","alluring","aloof","amazing","ambiguous","ambitious","amuck","amused","amusing","ancient","angry","animated","annoyed","annoying","anxious","apathetic","aquatic","aromatic","arrogant","ashamed","aspiring","assorted","astonishing","attractive","auspicious","automatic","available","average","awake","aware","awesome","awful","axiomatic",
    "bad","barbarous","bashful","bawdy","beautiful","befitting","belligerent","beneficial","bent","berserk","best","better","bewildered","big","billowy","bitter","bizarre","black","bloody","blue","blushing","boiling","boorish","bored","boring","bouncy","boundless","brainy","brash","brave","brawny","breakable","breezy","brief","bright","bright","broad","broken","brown","bumpy","burly","bustling","busy",
    "cagey","calculating","callous","calm","capable","capricious","careful","careless","caring","cautious","ceaseless","certain","changeable","charming","cheap","cheerful","chemical","chief","childlike","chilly","chivalrous","chubby","chunky","clammy","classy","clean","clear","clever","cloistered","cloudy","closed","clumsy","cluttered","coherent","cold","colorful","colossal","combative","comfortable","common","complete","complex","concerned","condemned","confused","conscious","cooing","cool","cooperative","coordinated","courageous","cowardly","crabby","craven","crazy","creepy","crooked","crowded","cruel","cuddly","cultured","cumbersome","curious","curly","curved","curvy","cut","cute","cute","cynical",
    "daffy","daily","damaged","damaging","damp","dangerous","dapper","dark","dashing","dazzling","dead","deadpan","deafening","dear","debonair","decisive","decorous","deep","deeply","defeated","defective","defiant","delicate","delicious","delightful","demonic","delirious","dependent","depressed","deranged","descriptive","deserted","detailed","determined","devilish","didactic","different","difficult","diligent","direful","dirty","disagreeable","disastrous","discreet","disgusted","disgusting","disillusioned","dispensable","distinct","disturbed","divergent","dizzy","domineering","doubtful","drab","draconian","dramatic","dreary","drunk","dry","dull","dusty","dusty","dynamic","dysfunctional",
    "eager","early","earsplitting","earthy","easy","eatable","economic","educated","efficacious","efficient","eight","elastic","elated","elderly","electric","elegant","elfin","elite","embarrassed","eminent","empty","enchanted","enchanting","encouraging","endurable","energetic","enormous","entertaining","enthusiastic","envious","equable","equal","erect","erratic","ethereal","evanescent","evasive","even","excellent","excited","exciting","exclusive","exotic","expensive","extra","exuberant","exultant",
    "fabulous","faded","faint","fair","faithful","fallacious","false","familiar","famous","fanatical","fancy","fantastic","far","fascinated","fast","fat","faulty","fearful","fearless","feeble","feigned","female","fertile","festive","few","fierce","filthy","fine","finicky","first","five","fixed","flagrant","flaky","flashy","flat","flawless","flimsy","flippant","flowery","fluffy","fluttering","foamy","foolish","foregoing","forgetful","fortunate","four","frail","fragile","frantic","free","freezing","frequent","fresh","fretful","friendly","frightened","frightening","full","fumbling","functional","funny","furry","furtive","future","futuristic","fuzzy",
    "gabby","gainful","gamy","gaping","garrulous","gaudy","general","gentle","giant","giddy","gifted","gigantic","glamorous","gleaming","glib","glistening","glorious","glossy","godly","good","goofy","gorgeous","graceful","grandiose","grateful","gratis","gray","greasy","great","greedy","green","grey","grieving","groovy","grotesque","grouchy","grubby","gruesome","grumpy","guarded","guiltless","gullible","gusty","guttural",
    "habitual","half","hallowed","halting","handsome","handsomely","handy","hanging","hapless","happy","hard","harmonious","harsh","hateful","heady","healthy","heartbreaking","heavenly","heavy","hellish","helpful","helpless","hesitant","hideous","high","highfalutin","hilarious","hissing","historical","holistic","hollow","homeless","homely","honorable","horrible","hospitable","hot","huge","hulking","humdrum","humorous","hungry","hurried","hurt","hushed","husky","hypnotic","hysterical",
    "icky","icy","idiotic","ignorant","ill","illegal","illustrious","imaginary","immense","imminent","impartial","imperfect","impolite","important","imported","impossible","incandescent","incompetent","inconclusive","industrious","incredible","inexpensive","infamous","innate","innocent","inquisitive","insidious","instinctive","intelligent","interesting","internal","invincible","irate","irritating","itchy",
    "jaded","jagged","jazzy","jealous","jittery","jobless","jolly","joyous","judicious","juicy","jumbled","jumpy","juvenile",
    "kaput","keen","kind","kindhearted","kindly","knotty","knowing","knowledgeable","known",
    "labored","lackadaisical","lacking","lame","lamentable","languid","large","last","late","laughable","lavish","lazy","lean","learned","left","legal","lethal","level","lewd","light","like","likeable","limping","literate","little","lively","lively","living","lonely","long","longing","loose","lopsided","loud","loutish","lovely","loving","low","lowly","lucky","ludicrous","lumpy","lush","luxuriant","lying","lyrical",
    "macabre","macho","maddening","madly","magenta","magical","magnificent","majestic","makeshift","male","malicious","mammoth","maniacal","many","marked","massive","married","marvelous","material","materialistic","mature","mean","measly","meaty","medical","meek","mellow","melodic","melted","merciful","mere","messy","mighty","military","milky","mindless","miniature","minor","miscreant","misty","mixed","moaning","modern","moldy","momentous","motionless","mountainous","muddled","mundane","murky","mushy","mute","mysterious",
    "naive","nappy","narrow","nasty","natural","naughty","nauseating","near","neat","nebulous","necessary","needless","needy","neighborly","nervous","new","next","nice","nifty","nimble","nine","nippy","noiseless","noisy","nonchalant","nondescript","nonstop","normal","nostalgic","nosy","noxious","null","numberless","numerous","nutritious","nutty",
    "oafish","obedient","obeisant","obese","obnoxious","obscene","obsequious","observant","obsolete","obtainable","oceanic","odd","offbeat","old","omniscient","one","onerous","open","opposite","optimal","orange","ordinary","organic","ossified","outgoing","outrageous","outstanding","oval","overconfident","overjoyed","overrated","overt","overwrought",
    "painful","painstaking","pale","paltry","panicky","panoramic","parallel","parched","parsimonious","past","pastoral","pathetic","peaceful","penitent","perfect","periodic","permissible","perpetual","petite","petite","phobic","physical","picayune","pink","piquant","placid","plain","plant","plastic","plausible","pleasant","plucky","pointless","poised","polite","political","poor","possessive","possible","powerful","precious","premium","present","pretty","previous","pricey","prickly","private","probable","productive","profuse","protective","proud","psychedelic","psychotic","public","puffy","pumped","puny","purple","purring","pushy","puzzled","puzzling",
    "quack","quaint","quarrelsome","questionable","quick","quickest","quiet","quirky","quixotic","quizzical",
    "rabid","racial","ragged","rainy","rambunctious","rampant","rapid","rare","raspy","ratty","ready","real","rebel","receptive","recondite","red","redundant","reflective","regular","relieved","remarkable","reminiscent","repulsive","resolute","resonant","responsible","rhetorical","rich","right","righteous","rightful","rigid","ripe","ritzy","roasted","robust","romantic","roomy","rotten","rough","round","royal","ruddy","rude","rural","rustic","ruthless",
    "sable","sad","safe","salty","same","sassy","satisfying","savory","scandalous","scarce","scared","scary","scattered","scientific","scintillating","scrawny","screeching","second","secret","secretive","sedate","seemly","selective","selfish","separate","serious","shaggy","shaky","shallow","sharp","shiny","shivering","shocking","short","shrill","shut","shy","sick","silent","silent","silky","silly","simple","simplistic","sincere","six","skillful","skinny","sleepy","slim","slimy","slippery","sloppy","slow","small","smart","smelly","smiling","smoggy","smooth","sneaky","snobbish","snotty","soft","soggy","solid","somber","sophisticated","sordid","sore","sore","sour","sparkling","special","spectacular","spicy","spiffy","spiky","spiritual","spiteful","splendid","spooky","spotless","spotted","spotty","spurious","squalid","square","squealing","squeamish","staking","stale","standing","statuesque","steadfast","steady","steep","stereotyped","sticky","stiff","stimulating","stingy","stormy","straight","strange","striped","strong","stupendous","stupid","sturdy","subdued","subsequent","substantial","successful","succinct","sudden","sulky","super","superb","superficial","supreme","swanky","sweet","sweltering","swift","symptomatic","synonymous",
    "taboo","tacit","tacky","talented","tall","tame","tan","tangible","tangy","tart","tasteful","tasteless","tasty","tawdry","tearful","tedious","teeny","telling","temporary","ten","tender","tense","tense","tenuous","terrible","terrific","tested","testy","thankful","therapeutic","thick","thin","thinkable","third","thirsty","thirsty","thoughtful","thoughtless","threatening","three","thundering","tidy","tight","tightfisted","tiny","tired","tiresome","toothsome","torpid","tough","towering","tranquil","trashy","tremendous","tricky","trite","troubled","truculent","true","truthful","two","typical",
    "ubiquitous","ugliest","ugly","ultra","unable","unaccountable","unadvised","unarmed","unbecoming","unbiased","uncovered","understood","undesirable","unequal","unequaled","uneven","unhealthy","uninterested","unique","unkempt","unknown","unnatural","unruly","unsightly","unsuitable","untidy","unused","unusual","unwieldy","unwritten","upbeat","uppity","upset","uptight","used","useful","useless","utopian","utter","uttermost",
    "vacuous","vagabond","vague","valuable","various","vast","vengeful","venomous","verdant","versed","victorious","vigorous","violent","violet","vivacious","voiceless","volatile","voracious","vulgar",
    "wacky","waggish","waiting","wakeful","wandering","wanting","warlike","warm","wary","wasteful","watery","weak","wealthy","weary","wet","whimsical","whispering","white","whole","wholesale","wicked","wide","wiggly","wild","willing","windy","wiry","wise","wistful","witty","woebegone","womanly","wonderful","wooden","woozy","workable","worried","worthless","wrathful","wretched","wrong","wry",
    "xenophobic","yellow","yielding","young","youthful","yummy","zany","zealous","zesty","zippy","zonked",
        ]
        self._NOUNS = [
            "a","ability","abroad","abuse","access","accident","account","act","action","active","activity","actor","ad","addition","address","administration","adult","advance","advantage","advertising","advice","affair","affect","afternoon","age","agency","agent","agreement","air","airline","airport","alarm","alcohol","alternative","ambition","amount","analysis","analyst","anger","angle","animal","annual","answer","anxiety","anybody","anything","anywhere","apartment","appeal","appearance","apple","application","appointment","area","argument","arm","army","arrival","art","article","aside","ask","aspect","assignment","assist","assistance","assistant","associate","association","assumption","atmosphere","attack","attempt","attention","attitude","audience","author","average","award","awareness",
            "baby","back","background","bad","bag","bake","balance","ball","band","bank","bar","base","baseball","basis","basket","bat","bath","bathroom","battle","beach","bear","beat","beautiful","bed","bedroom","beer","beginning","being","bell","belt","bench","bend","benefit","bet","beyond","bicycle","bid","big","bike","bill","bird","birth","birthday","bit","bite","bitter","black","blame","blank","blind","block","blood","blow","blue","board","boat","body","bone","bonus","book","boot","border","boss","bother","bottle","bottom","bowl","box","boy","boyfriend","brain","branch","brave","bread","break","breakfast","breast","breath","brick","bridge","brief","brilliant","broad","brother","brown","brush","buddy","budget","bug","building","bunch","burn","bus","business","button","buy","buyer",
            "cabinet","cable","cake","calendar","call","calm","camera","camp","campaign","can","cancel","cancer","candidate","candle","candy","cap","capital","car","card","care","career","carpet","carry","case","cash","cat","catch","category","cause","celebration","cell","chain","chair","challenge","champion","championship","chance","change","channel","chapter","character","charge","charity","chart","check","cheek","chemical","chemistry","chest","chicken","child","childhood","chip","chocolate","choice","church","cigarette","city","claim","class","classic","classroom","clerk","click","client","climate","clock","closet","clothes","cloud","club","clue","coach","coast","coat","code","coffee","cold","collar","collection","college","combination","combine","comfort","comfortable","command","comment","commercial","commission","committee","common","communication","community","company","comparison","competition","complaint","complex","computer","concentrate","concept","concern","concert","conclusion","condition","conference","confidence","conflict","confusion","connection","consequence","consideration","consist","constant","construction","contact","contest","context","contract","contribution","control","conversation","convert","cook","cookie","copy","corner","cost","count","counter","country","county","couple","courage","course","court","cousin","cover","cow","crack","craft","crash","crazy","cream","creative","credit","crew","criticism","cross","cry","culture","cup","currency","current","curve","customer","cut","cycle",
            "dad","damage","dance","dare","dark","data","database","date","daughter","day","dead","deal","dealer","dear","death","debate","debt","decision","deep","definition","degree","delay","delivery","demand","department","departure","dependent","deposit","depression","depth","description","design","designer","desire","desk","detail","development","device","devil","diamond","diet","difference","difficulty","dig","dimension","dinner","direction","director","dirt","disaster","discipline","discount","discussion","disease","dish","disk","display","distance","distribution","district","divide","doctor","document","dog","door","dot","double","doubt","draft","drag","drama","draw","drawer","drawing","dream","dress","drink","drive","driver","drop","drunk","due","dump","dust","duty",
            "ear","earth","ease","east","eat","economics","economy","edge","editor","education","effect","effective","efficiency","effort","egg","election","elevator","emergency","emotion","emphasis","employ","employee","employer","employment","end","energy","engine","engineer","engineering","entertainment","enthusiasm","entrance","entry","environment","equal","equipment","equivalent","error","escape","essay","establishment","estate","estimate","evening","event","evidence","exam","examination","example","exchange","excitement","excuse","exercise","exit","experience","expert","explanation","expression","extension","extent","external","extreme","eye",
            "face","fact","factor","fail","failure","fall","familiar","family","fan","farm","farmer","fat","father","fault","fear","feature","fee","feed","feedback","feel","feeling","female","few","field","fight","figure","file","fill","film","final","finance","finding","finger","finish","fire","fish","fishing","fix","flight","floor","flow","flower","fly","focus","fold","following","food","foot","football","force","forever","form","formal","fortune","foundation","frame","freedom","friend","friendship","front","fruit","fuel","fun","function","funeral","funny","future",
            "gain","game","gap","garage","garbage","garden","gas","gate","gather","gear","gene","general","gift","girl","girlfriend","give","glad","glass","glove","go","goal","god","gold","golf","good","government","grab","grade","grand","grandfather","grandmother","grass","great","green","grocery","ground","group","growth","guarantee","guard","guess","guest","guidance","guide","guitar","guy",
            "habit","hair","half","hall","hand","handle","hang","harm","hat","hate","head","health","hearing","heart","heat","heavy","height","hell","hello","help","hide","high","highlight","highway","hire","historian","history","hit","hold","hole","holiday","home","homework","honey","hook","hope","horror","horse","hospital","host","hotel","hour","house","housing","human","hunt","hurry","hurt","husband",
            "ice","idea","ideal","if","illegal","image","imagination","impact","implement","importance","impress","impression","improvement","incident","income","increase","independence","independent","indication","individual","industry","inevitable","inflation","influence","information","initial","initiative","injury","insect","inside","inspection","inspector","instance","instruction","insurance","intention","interaction","interest","internal","international","internet","interview","introduction","investment","invite","iron","island","issue","it","item",
            "jacket","job","join","joint","joke","judge","judgment","juice","jump","junior","jury",
            "keep","key","kick","kid","kill","kind","king","kiss","kitchen","knee","knife","knowledge",
            "lab","lack","ladder","lady","lake","land","landscape","language","laugh","law","lawyer","lay","layer","lead","leader","leadership","leading","league","leather","leave","lecture","leg","length","lesson","let","letter","level","library","lie","life","lift","light","limit","line","link","lip","list","listen","literature","living","load","loan","local","location","lock","log","long","look","loss","love","low","luck","lunch",
            "machine","magazine","mail","main","maintenance","major","make","male","mall","man","management","manager","manner","manufacturer","many","map","march","mark","market","marketing","marriage","master","match","mate","material","math","matter","maximum","maybe","meal","meaning","measurement","meat","media","medicine","medium","meet","meeting","member","membership","memory","mention","menu","mess","message","metal","method","middle","midnight","might","milk","mind","mine","minimum","minor","minute","mirror","miss","mission","mistake","mix","mixture","mobile","mode","model","mom","moment","money","monitor","month","mood","morning","mortgage","most","mother","motor","mountain","mouse","mouth","move","movie","mud","muscle","music",
            "nail","name","nasty","nation","national","native","natural","nature","neat","necessary","neck","negative","negotiation","nerve","net","network","news","newspaper","night","nobody","noise","normal","north","nose","note","nothing","notice","novel","number","nurse",
            "object","objective","obligation","occasion","offer","office","officer","official","oil","one","opening","operation","opinion","opportunity","opposite","option","orange","order","ordinary","organization","original","other","outcome","outside","oven","owner",
            "pace","pack","package","page","pain","paint","painting","pair","panic","paper","parent","park","parking","part","particular","partner","party","pass","passage","passenger","passion","past","path","patience","patient","pattern","pause","pay","payment","peace","peak","pen","penalty","pension","people","percentage","perception","performance","period","permission","permit","person","personal","personality","perspective","phase","philosophy","phone","photo","phrase","physical","physics","piano","pick","picture","pie","piece","pin","pipe","pitch","pizza","place","plan","plane","plant","plastic","plate","platform","play","player","pleasure","plenty","poem","poet","poetry","point","police","policy","politics","pollution","pool","pop","population","position","positive","possession","possibility","possible","post","pot","potato","potential","pound","power","practice","preference","preparation","presence","present","presentation","president","press","pressure","price","pride","priest","primary","principle","print","prior","priority","private","prize","problem","procedure","process","produce","product","profession","professional","professor","profile","profit","program","progress","project","promise","promotion","prompt","proof","property","proposal","protection","psychology","public","pull","punch","purchase","purple","purpose","push","put",
            "quality","quantity","quarter","queen","question","quiet","quit","quote",
            "race","radio","rain","raise","range","rate","ratio","raw","reach","reaction","read","reading","reality","reason","reception","recipe","recognition","recommendation","record","recording","recover","red","reference","reflection","refrigerator","refuse","region","register","regret","regular","relation","relationship","relative","release","relief","remote","remove","rent","repair","repeat","replacement","reply","report","representative","republic","reputation","request","requirement","research","reserve","resident","resist","resolution","resolve","resort","resource","respect","respond","response","responsibility","rest","restaurant","result","return","reveal","revenue","review","revolution","reward","rice","rich","ride","ring","rip","rise","risk","river","road","rock","role","roll","roof","room","rope","rough","round","routine","row","royal","rub","ruin","rule","run","rush",
            "sad","safe","safety","sail","salad","salary","sale","salt","sample","sand","sandwich","satisfaction","save","savings","scale","scene","schedule","scheme","school","science","score","scratch","screen","screw","script","sea","search","season","seat","second","secret","secretary","section","sector","security","selection","self","sell","senior","sense","sensitive","sentence","series","serve","service","session","set","setting","sex","shake","shame","shape","share","she","shelter","shift","shine","ship","shirt","shock","shoe","shoot","shop","shopping","shot","shoulder","show","shower","sick","side","sign","signal","signature","significance","silly","silver","simple","sing","singer","single","sink","sir","sister","site","situation","size","skill","skin","skirt","sky","sleep","slice","slide","slip","smell","smile","smoke","snow","society","sock","soft","software","soil","solid","solution","somewhere","son","song","sort","sound","soup","source","south","space","spare","speaker","special","specialist","specific","speech","speed","spell","spend","spirit","spiritual","spite","split","sport","spot","spray","spread","spring","square","stable","staff","stage","stand","standard","star","start","state","statement","station","status","stay","steak","steal","step","stick","still","stock","stomach","stop","storage","store","storm","story","strain","stranger","strategy","street","strength","stress","stretch","strike","string","strip","stroke","structure","struggle","student","studio","study","stuff","stupid","style","subject","substance","success","suck","sugar","suggestion","suit","summer","sun","supermarket","support","surgery","surprise","surround","survey","suspect","sweet","swim","swimming","swing","switch","sympathy","system",
            "table","tackle","tale","talk","tank","tap","target","task","taste","tax","tea","teach","teacher","teaching","team","tear","technology","telephone","television","tell","temperature","temporary","tennis","tension","term","test","text","thanks","theme","theory","thing","thought","throat","ticket","tie","till","time","tip","title","today","toe","tomorrow","tone","tongue","tonight","tool","tooth","top","topic","total","touch","tough","tour","tourist","towel","tower","town","track","trade","tradition","traffic","train","trainer","training","transition","transportation","trash","travel","treat","tree","trick","trip","trouble","truck","trust","truth","try","tune","turn","twist","two","type",
            "uncle","understanding","union","unique","unit","university","upper","upstairs","use","user","usual",
            "vacation","valuable","value","variation","variety","vast","vegetable","vehicle","version","video","view","village","virus","visit","visual","voice","volume",
            "wait","wake","walk","wall","war","warning","wash","watch","water","wave","way","weakness","wealth","wear","weather","web","wedding","week","weekend","weight","weird","welcome","west","western","wheel","whereas","while","white","whole","wife","will","win","wind","window","wine","wing","winner","winter","wish","witness","woman","wonder","wood","word","work","worker","working","world","worry","worth","wrap","writer","writing",
            "yard","year","yellow","yesterday","you","young","youth","zone"
        ]
        self._previously_used = set()
    
    def get_name(self):
        while True:
            name = "alias_" + random.choice(self._ADJECTIVES) + "_" + random.choice(self._NOUNS)
            if name not in self._previously_used:
                break
        self._previously_used.add(name)
        return name

class ConfLevel(IntEnum):
    WHITE = 0
    GREEN = 1
    AMBER = 2
    RED = 3

class ConfLevelManager:
    def __init__(self,conf_level) -> None:
        if isinstance(conf_level,str):
            self.conf_level = ConfLevelManager.get_conf_lvl_from_str(conf_level)
        else:
            self.conf_level = conf_level
    
    @staticmethod
    def get_conf_lvl_from_str(str_:str) -> ConfLevel:
        """Converts a string to a ConfLevel enum value.

        Args:
            str_ (str): The string to convert.

        Returns:
            ConfLevel: The ConfLevel enum value.
        """
        aliases = {
            ConfLevel.WHITE : {
                'a : tlp:white',
                'a - tlp:white',
                'tlp:white',
                'white',
            },
            ConfLevel.GREEN : {
                'b : tlp:green',
                'b - tlp:green',
                'tlp:green',
                'green',
            },
            ConfLevel.AMBER : {
                'c : tlp:amber',
                'c - tlp:amber',
                'tlp:amber',
                'amber',
            },
            ConfLevel.RED : {
                'd : tlp:red',
                'd - tlp:red',
                'tlp:red',
                'red',
            }
        }
        for key, value in aliases.items():
            if str_.lower().strip() in value:
                return key
        return None
    
    def is_allowed(self, conf_level) -> bool:
        """Checks if a given ConfLevel is allowed, against the default of the Manager.

        Args:
            conf_level (ConfLevel | str): The confidence level to check against.

        Returns:
            bool: True if the confidence level is allowed, False otherwise.
        """
        if isinstance(conf_level, str):
            return ConfLevelManager.get_conf_lvl_from_str(conf_level) <= self.conf_level
        return conf_level <= self.conf_level

class Sanitizer:
    def __init__(self, conf_level) -> None:
        self.conf_level_manager = ConfLevelManager(conf_level)
        self.random_name_generator = RandomNameGenerator()
        self.aliases = dict()

        self.protected_keys = {
            'hasConfidentiality',
            'hasNextStep',
            'hasPreviousStep',
            'hasInitialStep',
            'hasFinalStep',
            'hasIntermediateStep',
            'hasExclusiveChoiceStep',
            'hasOptionalStep',
            'isStepOf',
        }
    
    def sanitize(self,pages:dict):
        """Sanitizes a string, based on the confidence level.

        Args:
            pages (dict): The dictionary of pages to sanitize.

        Returns:
            dict: The sanitized dictionary.
        """

        sntzd_pages = dict()

        for page_id, page in pages.items(): # Walk through all pages
            # Get the confidence level of the page
            page_conf_lvl = page.get('hasConfidentiality',['tlp:red'])[0]
            if not self.conf_level_manager.is_allowed(page_conf_lvl): # If the page is not allowed, sanitize it
                for key in page:
                    if key not in self.protected_keys:
                        page[key] = []
                self.aliases[page_id] = self.random_name_generator.get_name()
        
        # implement aliases
        for page_id, page in pages.items():
            for key in page:
                snt_entry = []
                for value in page[key]:
                    if value in self.aliases:
                        snt_entry.append(self.aliases[value])
                    else:
                        snt_entry.append(value)
                page[key] = snt_entry
            if page_id in self.aliases:
                sntzd_pages[self.aliases[page_id]] = page
            else:
                sntzd_pages[page_id] = page
        
        return sntzd_pages
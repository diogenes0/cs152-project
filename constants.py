START_KEYWORD = "report"
CANCEL_KEYWORD = "cancel"
HELP_KEYWORD = "help"
CONFIRM_KEYWORD = "yes"

SPAM_KEYWORD = "spam"

FRAUD_KEYWORD = "fraud"
F_IMPERSONATION_KEYWORD = "impersonation"
F_ACCOUNT_KEYWORD = "compromised account"
F_SOLICITATION_KEYWORD = "monetary solicitation"
F_OTHER_KEYWORD = "other"

HATE_KEYWORD = "hate speech/harassment"
H_RACE_KEYWORD = "race"
H_ETHNICITY_KEYWORD = "ethnicity"
H_NATIONALITY_KEYWORD = "nationality"
H_SEXUAL_KEYWORD = "sexual orientation"
H_GENDER_KEYWORD = "gender"
H_RELIGION_KEYWORD = "religion"
H_AGE_KEYWORD = "age"
H_ABILITY_KEYWORD = "ability"
H_OTHER_KEYWORD = "other"

VIOLENCE_KEYWORD = "violence"
V_OTHERS_KEYWORD = "toward others"
V_SELF_KEYWORD = "self harm"
V_SUICIDE_KEYWORD = "suicide"
V_OTHER_KEYWORD = "other"

INTIMATE_KEYWORD = "intimate materials"
I_SEXUAL_KEYWORD = "sexually explicit materials"
I_PI_KEYWORD = "personal information"
I_OTHER_KEYWORD = "other"

OTHER_KEYWORD = "other"
O_GOODS_KEYWORD = "illegal goods"
O_THEFT_KEYWORD = "theft"
O_VANDALISM_KEYWORD = "vandalism"
O_OTHER_KEYWORD = "other"

AUTO_KEYWORD = "auto moderated"

MOD_LAW = "law" 			# incident is reported to law enforcement
MOD_M_DEMOTE = "m_demote" 	# message is demoted in search
MOD_M_HIDE = "m_hide" 		# message is hidden on platform. No user can access it
MOD_M_SHADOW = "m_shadow"	# message is hidden from world. Available to poster
MOD_U_DEMOTE = "u_demote"	# user is demoted in search and recommendations
MOD_U_HIDE = "u_hide"		# user is hidden in search and recommendations
MOD_U_SHADOW = "u_shadow"	# user is shadowbanned. Nothing they do is visible to anyone but them
MOD_U_SUSPEND = "u_suspend"	# users is suspended from platform temporarily
MOD_U_BAN = "u_ban"			# user is banned from platform. account is deactivated
MOD_U_NONE = "none"			# no action is taken

EMOJI_LAW = "👮"
EMOJI_DEMOTE = "⬇"
EMOJI_HIDE = "🦝"
EMOJI_SHADOW = "👻"

TYPES = [SPAM_KEYWORD, FRAUD_KEYWORD, HATE_KEYWORD, VIOLENCE_KEYWORD, INTIMATE_KEYWORD, OTHER_KEYWORD]

SPAM_TYPES = [SPAM_KEYWORD]
FRAUD_TYPES = [F_IMPERSONATION_KEYWORD, F_ACCOUNT_KEYWORD, F_SOLICITATION_KEYWORD, F_OTHER_KEYWORD]
HATE_TYPES = [H_RACE_KEYWORD, H_ETHNICITY_KEYWORD, H_NATIONALITY_KEYWORD, H_SEXUAL_KEYWORD, H_GENDER_KEYWORD, 
                H_RELIGION_KEYWORD, H_AGE_KEYWORD, H_ABILITY_KEYWORD, H_OTHER_KEYWORD]
VIOLENCE_TYPES = [V_OTHERS_KEYWORD, V_SELF_KEYWORD, V_SUICIDE_KEYWORD, V_OTHER_KEYWORD]
INTIMATE_TYPES = [I_SEXUAL_KEYWORD, I_PI_KEYWORD, I_OTHER_KEYWORD]
OTHER_TYPES = [O_GOODS_KEYWORD, O_THEFT_KEYWORD, O_VANDALISM_KEYWORD, O_OTHER_KEYWORD]
#!/usr/bin/make -f
# Used colors ANSI modifiers escape codes
 color_green := 32
 color_red := 31
 color_yellow := 33

# Newline - comes handy in some situations
define \n


endef

# Command message - display basic info about the command, and run it.
define cmd
@$(if $(MAKE_FULL_LOG),,\
printf "\033[1;""$4""m>\033[0m \033[1m%s\033[0m %s\n" "$1" "$2";)
	$(if $(MAKE_FULL_LOG),,@)$3
endef

# Quiet command - make it non-quiet if full log is enabled.
define qcmd
$(if $(MAKE_FULL_LOG),,@)$1
endef

# Unconditionnal message.
define amsg
@printf "\033[1;""$(color_green)""m>\033[0m \033[1m%s\033[0m\n" "$1"
endef

# Normal message - display it.
define msg
$(if $(MAKE_FULL_LOG),,\
@printf "\033[1;""$2""m>\033[0m \033[1m%s\033[0m\n" "$1")
endef

# Build command
define bcmd
$(call cmd,$1,$2,$3,$(color_green))
endef

# Build message
define bmsg
$(call msg,$1,$(color_green))
endef

# Remove message
define rmsg
$(call msg,$1,$(color_red))
endef

# Install message
define imsg
$(call msg,$1,$(color_yellow))
endef

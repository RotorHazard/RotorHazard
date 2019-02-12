/* Articulate.js (1.1.0). (C) 2017 Adam Coti. MIT @license: en.wikipedia.org/wiki/MIT_License

   See Github page at: https://github.com/acoti/articulate.js
   See Web site at: http://articulate.purefreedom.com

*/


(function($) {
    "use strict";

    var ignoreTagsUser = new Array();
    var recognizeTagsUser = new Array();
    var replacements = new Array();
    var customTags = new Array();

    var rateDefault = 1.10;
    var pitchDefault = 1;
    var volumeDefault = 1;

    var rateUserDefault;
    var pitchUserDefault;
    var volumeUserDefault;
    var voiceUserDefault;

    var rate = rateDefault;
    var pitch = pitchDefault;
    var volume = volumeDefault;
    var voices = new Array();

    function voiceTag(prepend,append) {
      this.prepend = prepend;
      this.append = append;
    }

    function voiceObj(name,language) {
      this.name = name;
      this.language = language;
    }





    // This populates the "voices" array with objects that represent the available voices in the 
    // current browser. Each object has two properties: name and language. It is loaded 
    // asynchronously in deference to Chrome.

    function populateVoiceList() {
        var systemVoices = speechSynthesis.getVoices();
        for(var i = 0; i < systemVoices.length ; i++) {
            voices.push(new voiceObj(systemVoices[i].name,systemVoices[i].lang));
        }
    }

    populateVoiceList();

    if (typeof speechSynthesis !== 'undefined' && speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = populateVoiceList;
    }


    // After checking for compatability, define the utterance object and then cancel the speech 
    // immediately even though nothing is yet spoken. This is to fix a quirk in Windows Chrome.

    if ("speechSynthesis" in window) {
        var speech = new SpeechSynthesisUtterance();
        window.speechSynthesis.cancel();
    }


    // Hated to do a browser detect, but Windows Chrome is a bit buggy and inconsistent with the default
    // voice that it uses unless that default voice ('native') is specified directly -- see line 165.
    // Every browser is fine with 'native' specified directly except Microsoft Edge, which is why
    // this browser detect ened up necessary for the time being. I think this will all resolve itself
    // in future browser versions, but for now, I felt this was the safest solution. But I feel dirty.

    var chrome = /chrome/i.test( navigator.userAgent );
    var edge = /edge/i.test( navigator.userAgent );
    var isChrome = ((chrome) && (!edge));


    var methods = {
        speak : function(options) {
            var opts = $.extend( {}, $.fn.articulate.defaults, options );

            var toSpeak = "";
            var obj, processed, finished;
            var voiceTags = new Array();


            // Default values.

            voiceTags["q"] = new voiceTag("quote,",", unquote,");
            voiceTags["ol"] = new voiceTag("Start of list.","End of list.");
            voiceTags["ul"] = new voiceTag("Start of list.","End of list.");
            voiceTags["blockquote"] = new voiceTag("Blockquote start.","Blockquote end.");
            voiceTags["img"] = new voiceTag("There's an embedded image with the description,","");
            voiceTags["table"] = new voiceTag("There's an embedded table with the caption,","");
            voiceTags["figure"] = new voiceTag("There's an embedded figure with the caption,","");

            var ignoreTags = ["audio","button","canvas","code","del","dialog","dl","embed","form","head","iframe","meter","nav","noscript","object","s","script","select","style","textarea","video"];


            // Check to see if the browser supports the functionality.

            if (!("speechSynthesis" in window)) {
                alert("Sorry, this browser does not support the Web Speech API.");
                return
            };


            // If something is currently being spoken, ignore new voice request. Otherwise it would be queued,
            // which is doable if someone wanted that, but not what I wanted.

            if (window.speechSynthesis.speaking) {
                return
            };


            // Cycle through all the elements in the original jQuery selector, process and clean
            // them one at a time, and continually append it to the variable "toSpeak".

            this.each(function() {
                obj = $(this).clone();                    // clone the DOM node and its descendants of what the user wants spoken
                processed = processDOMelements(obj);      // process and manipulate DOM tree of this clone
                processed = jQuery(processed).html();     // convert the result of all that to a string
                finished = cleanDOMelements(processed);   // do some text manipulation
                toSpeak = toSpeak + " " + finished;       // add it to what will ultimately be spoken after cycling through selectors
            });


            // Check if users have set their own rate/pitch/volume defaults, otherwise use defaults.

            if (rateUserDefault !== undefined) {
                rate = rateUserDefault;
            } else {
                rate = rateDefault;
            }

            if (pitchUserDefault !== undefined) {
                pitch = pitchUserDefault;
            } else {
                pitch = pitchDefault;
            }

            if (volumeUserDefault !== undefined) {
                volume = volumeUserDefault;
            } else {
                volume = volumeDefault;
            }


            // To debug, un-comment the following to see exactly what's about to be spoken.
            // console.log(toSpeak);

            // This is where the magic happens. Well, not magic, but at least we can finally hear something.
            // After the line that fixes the Windows Chrome quirk, the custom voice is set if one has been chosen.
            
            speech = new SpeechSynthesisUtterance();
            speech.text = toSpeak;
            speech.rate = rate;
            speech.pitch = pitch;
            speech.volume = volume;
            if (isChrome) { speech.voice = speechSynthesis.getVoices().filter(function(voice) { return voice.name == "native"; })[0]; };
            if (voiceUserDefault !== undefined) { speech.voice = speechSynthesis.getVoices().filter(function(voice) { return voice.name == voiceUserDefault; })[0]; };
            window.speechSynthesis.speak(speech);



            function processDOMelements(clone) {

                var copy, prepend;


                // Remove tags from the "ignoreTags" array because the user called "articulate('recognize')"
                // and said he/she doesn't want some tags un-spoken. Double negative there, but it does make sense.

                if (recognizeTagsUser.length > 0) {
                    for (var prop in recognizeTagsUser) {
                        var index = ignoreTags.indexOf(recognizeTagsUser[prop]);
                        if (index > -1) {
                            ignoreTags.splice(index, 1);
                        }
                    };
                };


                // Remove DOM objects from those listed in the "ignoreTags" array now that the user has specified 
                // which ones, if any, he/she wants to keep.

                for (var prop in ignoreTags) {
                    jQuery(clone).find(ignoreTags[prop]).addBack(ignoreTags[prop]).not("[data-articulate-recognize]").each(function() {
                        jQuery(this).html("");
                    });
                };


                // Remove DOM objects as specified in the "ignoreTagsUser" array that the user specified when 
                // calling "articulate('ignore')".

                if (ignoreTagsUser.length > 0) {
                    for (var prop in ignoreTagsUser) {
                        jQuery(clone).find(ignoreTagsUser[prop]).addBack(ignoreTagsUser[prop]).not("[data-articulate-recognize]").each(function() {
                            jQuery(this).html("");
                        });
                    };
                };


                // Remove DOM objects as specified in the HTML with "data-articulate-ignore".

                jQuery(clone).find("[data-articulate-ignore]").addBack("[data-articulate-ignore]").each(function() {
                    jQuery(this).html("");
                });


                // Search for prepend data as specified in the HTML with "data-articulate-prepend".

                jQuery(clone).find("[data-articulate-prepend]").addBack("[data-articulate-prepend]").each(function() {
                    copy = jQuery(this).data("articulate-prepend");
                    jQuery(this).prepend(copy + " ");
                });


                // Search for append data as specified in the HTML with "data-articulate-append".

                jQuery(clone).find("[data-articulate-append]").addBack("[data-articulate-append]").each(function() {
                    copy = jQuery(this).data("articulate-append");
                    jQuery(this).append(" " + copy);
                });


                // Search for tags to prepend and append as specified by the "voiceTags" array.

                var count = 0;

                for (var tag in voiceTags) {
                    count++
                    if (count <= 4) {
                        jQuery(clone).find(tag).each(function() {
                            if (customTags[tag]) {
                                jQuery(this).prepend(customTags[tag].prepend + " ");
                                jQuery(this).append(" " + customTags[tag].append);
                            } else {
                                jQuery(this).prepend(voiceTags[tag].prepend + " ");
                                jQuery(this).append(" " + voiceTags[tag].append);
                            };
                        });
                    };
                };


                // Search for <h1> through <h6> and <li> and <br> to add a pause at the end of those tags. This is done
                // because these tags require a pause, but often don't have a comma or period at the end of their text.

                jQuery(clone).find("h1,h2,h3,h4,h5,h6,li,p").addBack("h1,h2,h3,h4,h5,h6,li,p").each(function() {
                    jQuery(this).append(". ");
                });

                jQuery(clone).find("br").each(function() {
                    jQuery(this).after(", ");
                });


                // Search for <figure>, check for <figcaption>, insert that text if it exists
                // and then remove the whole DOM object

                jQuery(clone).find("figure").addBack("figure").each(function() {
                    copy = jQuery(this).find("figcaption").html();
                    if (customTags["figure"]) {
                        prepend = customTags["figure"].prepend
                    }
                    else {
                        prepend = voiceTags["figure"].prepend
                    }
                    if ((copy != undefined) && (copy !== "")) {
                        jQuery("<div>" + prepend + " " + copy + ".</div>").insertBefore(this);
                    }
                    jQuery(this).remove();
                });


                // Search for <image>, check for ALT attribute, insert that text if it exists and then 
                // remove the whole DOM object. Had to make adjustments for nesting in <picture> tags.

                jQuery(clone).find("img").addBack("img").each(function() {
                    copy = jQuery(this).attr("alt");
                    var parent = jQuery(this).parent();
                    var parentName = parent.get(0).tagName;

                    if (customTags["img"]) {
                        prepend = customTags["img"].prepend
                    }
                    else {
                        prepend = voiceTags["img"].prepend
                    };

                    if ((copy !== undefined) && (copy != "")) {
                        if (parentName == "PICTURE") {
                            var par
                            jQuery("<div>" + prepend + " " + copy + ".</div>").insertBefore(parent);
                        } else {
                            jQuery("<div>" + prepend + " " + copy + ".</div>").insertBefore(this);
                        }
                    };
                    jQuery(this).remove();
                });


                // Search for <table>, check for <caption>, insert that text if it exists
                // and then remove the whole DOM object.

                jQuery(clone).find("table").addBack("table").each(function() {
                    copy = jQuery(this).find("caption").text();
                    if (customTags["table"]) {
                        prepend = customTags["table"].prepend
                    }
                    else {
                        prepend = voiceTags["table"].prepend
                    }
                    if ((copy !== undefined) && (copy != "")) {
                        jQuery("<div>" + prepend + " " + copy + ".</div>").insertBefore(this);
                    }
                    jQuery(this).remove();
                });

                
                // Search for DOM object to be replaced as specified in the HTML with "data-articulate-swap".

                jQuery(clone).find("[data-articulate-swap]").addBack("[data-articulate-swap]").each(function() {
                    copy = jQuery(this).data("articulate-swap");
                    jQuery(this).text(copy);
                });


                // Search for DOM object to spelled out as specified in the HTML with "data-articulate-spell".
                // I find this function fun if, admittedly, not too practical.

                jQuery(clone).find("[data-articulate-spell]").addBack("[data-articulate-spell]").each(function() {
                    copy = jQuery(this).text();
                    copy = copy.split("").join(" ");
                    jQuery(this).text(copy);
                });


                return clone;
            }



            function cleanDOMelements(final) {

                var start,ended,speak,part1,part2,final;


                // Search for <articulate> in comments, copy the text, place it outside the comment,
                // and then splice together "final" string again, which omits the comment.

                while (final.indexOf("<!-- <articulate>") != -1) {
                    start = final.indexOf("<!-- <articulate>");
                    ended = final.indexOf("</articulate> -->",start);
                    
                    if (ended == -1) { break; }

                    speak = final.substring(start + 17,ended);
                    part1 = final.substring(0,start);
                    part2 = final.substring(ended + 17);
                    final = part1 + " " + speak + " " + part2;
                };


                // Strip out remaining comments.

                final = final.replace(/<!--[\s\S]*?-->/g,"");


                // Strip out remaining HTML tags.

                final = final.replace(/(<([^>]+)>)/ig,"");

                
                // Replace a string of characters with another as specified by "articulate('replace')".

                var len = replacements.length;
                var i = 0;
                var old, rep;

                while (i < len) {
                    old = replacements[i];
                    old = old.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
                    rep = replacements[i + 1] + " ";
                    var regexp = new RegExp(old, "gi");
                    var final = final.replace(regexp,rep);
                    i = i + 2;
                };


                // Replace double smart quotes with proper text, same as what was done previously with <q>.

                if (customTags["q"]) {
                    final = final.replace(/“/g,customTags["q"].prepend + " ");
                    final = final.replace(/”/g," " + customTags["q"].append);
                } else {
                    final = final.replace(/“/g,voiceTags["q"].prepend + " ");
                    final = final.replace(/”/g," " + voiceTags["q"].append);
                }


                // Replace em-dashes and double-dashes with a pause since the browser doesn't do so when reading.

                final = final.replace(/—/g, ", ");
                final = final.replace(/--/g, ", ");


                // When read from the DOM, a few special characters (&amp; for example) display as their hex codes
                // rather than resolving into their actual character -- this technique fixes that.

                var txt = document.createElement("textarea");
                txt.innerHTML = final;
                final = txt.value;


                // Strip out new line characters and carriage returns, which cause unwanted pauses.

                final = final.replace(/(\r\n|\n|\r)/gm,"");


                // Strip out multiple spaces and periods and commas -- for neatness more than anything else since
                // none of this will affect the speech. But it helps when checking progress in the console.

                final = final.replace(/  +/g, ' ');
                final = final.replace(/\.\./g, '.');
                final = final.replace(/,,/g, ',');
                final = final.replace(/ ,/g, ',');

                return final;
            }

            return this;
        },


        // All the functions for Articulate.js.

        pause : function() {
            window.speechSynthesis.pause();
            return this;
        },


        resume : function() {
            window.speechSynthesis.resume();
            return this;
        },


        stop : function() {
            window.speechSynthesis.cancel();
            return this;
        },


        enabled : function() {
            return ("speechSynthesis" in window);
        },


        isSpeaking : function() {
            return (window.speechSynthesis.speaking);
        },


        isPaused : function() {
            return (window.speechSynthesis.paused);
        },


        rate : function() {
            var num = arguments[0];
            if ((num >= 0.1) && (num <= 10)) {
                rateUserDefault = num;
            } else if (num === undefined) {
                rateUserDefault = void 0;
                rate = rateDefault;
            };
            return this;
        },


        pitch : function() {
            var num = arguments[0];
            if ((num >= 0.1) && (num <= 2)) {
                pitchUserDefault = num;
            } else if (num === undefined) {
                pitchUserDefault = void 0;
                pitch = pitchDefault;
            };
            return this;
        },


        volume : function() {
            var num = arguments[0];
            if ((num >= 0) && (num <= 1)) {
                volumeUserDefault = num;
            } else if (num === undefined) {
                volumeUserDefault = void 0;
                volume = volumeDefault;
            };
            return this;
        },


        ignore : function() {
            var len = arguments.length;
            ignoreTagsUser.length = 0;
            while (len > 0) {
                len--;
                ignoreTagsUser.push(arguments[len]);
            };
            return this;
        },


        recognize : function() {
            var len = arguments.length;
            recognizeTagsUser.length = 0;
            while (len > 0) {
                len--;
                recognizeTagsUser.push(arguments[len]);
            };
            return this;
        },


        replace : function() {
            var len = arguments.length;
            replacements.length = 0;
            var i = 0;
            while (i < len) {
                replacements.push(arguments[i], arguments[i + 1]);
                i = i + 2;
                if ((len - i) == 1) { break; };
            };
            return this;
        },


        customize : function() {
            var len = arguments.length;
            if (len == 0) {
                customTags = [];
            };
            if (len == 2) {
                if (["img","table","figure"].indexOf(arguments[0]) == -1) { console.log("Error: When customizing, tag indicated must be either 'img', 'table', or 'figure'."); return; }
                customTags[arguments[0].toString()] = new voiceTag(arguments[1].toString());
            };
            if (len == 3) {
                if (["q","ol","ul","blockquote"].indexOf(arguments[0]) == -1) { console.log("Error: When customizing, tag indicated must be either 'q', 'ol', 'ul' or 'blockquote'."); return; }
                customTags[arguments[0].toString()] = new voiceTag(arguments[1].toString(), arguments[2].toString());
            };
            return this;
        },

        
        getVoices : function() {


            // If no arguments, then the user has requested the array of voices populated earlier.
            
            if (arguments.length == 0) {
                return voices;
            };


            // If there's another argument, we'll assume it's a jQuery selector designating where to put the dropdown menu.
            // And if there's a third argument, that will be custom text for the dropdown menu.
            // Then we'll create a dropdown menu with the voice names and, in parenthesis, the language code.
            
            var obj = jQuery(arguments[0]);
            var customTxt = "Choose a Different Voice";

            if (arguments[1] !== undefined) {
                customTxt = arguments[1];
            };

            obj.append(jQuery("<select id='voiceSelect'><option value='none'>" + customTxt + "</option></select>"));
            for(var i = 0; i < voices.length ; i++) {
                var option = document.createElement('option');
                option.textContent = voices[i].name + ' (' + voices[i].language + ')';
                option.setAttribute('value', voices[i].name);
                option.setAttribute('data-articulate-language', voices[i].language);
                obj.find("select").append(option);
            }


            // Add an onchange event to the dropdown menu.
            
            obj.on('change', function() {
                jQuery(this).find("option:selected").each(function() {
                    if (jQuery(this).val() != "none") {
                        voiceUserDefault = jQuery(this).val();
                    }
                });
            });
            return this;
        },


        setVoice : function() {


            // The setVoice function has to have two attributes -- if not, exit the function.
            
            if (arguments.length < 2) {
                return this
            }

            var requestedVoice, requestedLanguage;


            // User wants to change the voice directly. If that name indeed exists, update the "voiceUserDefault" variable.
            
            if (arguments[0] == "name") {
                requestedVoice = arguments[1];
                for (var i = 0; i < voices.length; i++) {
                    if (voices[i].name == requestedVoice) {
                        voiceUserDefault = requestedVoice;
                    };
                };
            };


            // User wants to change the voice by only specifying the first two characters of the language code. Case insensitive.
            
            if (arguments[0] == "language") {
                requestedLanguage = arguments[1].toUpperCase();
                if (requestedLanguage.length == 2) {
                    for (var i = 0; i < voices.length; i++) {
                        if (voices[i].language.substring(0,2).toUpperCase() == requestedLanguage) {
                            voiceUserDefault = voices[i].name;
                            break
                        };
                    };
                } else {


                    // User wants to change the voice by specifying the complete language code.
            
                    for (var i = 0; i < voices.length; i++) {
                        if (voices[i].language == requestedLanguage) {
                            voiceUserDefault = voices[i].name;
                            break
                        };
                    };
                }
            };
            return this;
        },

    };




    $.fn.articulate = function(method) {

        if (methods[method]) {
            return methods[method].apply( this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === "object" || ! method) {
            return methods.speak.apply(this, arguments);
        } else {
            jQuery.error("Method " +  method + " does not exist on jQuery.articulate");
        }

    };


}(jQuery));

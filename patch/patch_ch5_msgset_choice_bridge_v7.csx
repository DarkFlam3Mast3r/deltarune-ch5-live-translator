using System;
using UndertaleModLib.Compiler;

EnsureDataLoaded();

string msgsetCode = @"
function msgset(arg0, arg1)
{
    global.msgno = arg0;
    global.msg[arg0] = arg1;

    var _ch5_bridge_text = string(arg1);

    if (arg0 == 0 || !variable_global_exists(""ch5_bridge_dialogue""))
    {
        global.ch5_bridge_dialogue = """";
    }

    global.ch5_bridge_dialogue += string(arg0) + "": "" + _ch5_bridge_text + chr(10);

    var _ch5_full_text = global.ch5_bridge_dialogue;
    if (string_pos(""\\C"", _ch5_bridge_text) > 0 && variable_global_exists(""choicemsg"") && is_array(global.choicemsg))
    {
        var _ch5_choice_text = """";
        var _ch5_choice_len = min(4, array_length(global.choicemsg));
        for (var _ch5_i = 0; _ch5_i < _ch5_choice_len; _ch5_i++)
        {
            var _ch5_choice_line = string(global.choicemsg[_ch5_i]);
            if (_ch5_choice_line != """" && _ch5_choice_line != "" "" && _ch5_choice_line != ""undefined"")
            {
                _ch5_choice_text += string(_ch5_i + 1) + "": "" + _ch5_choice_line + chr(10);
            }
        }
        if (_ch5_choice_text != """")
        {
            _ch5_full_text += chr(10) + ""[CHOICE]"" + chr(10) + _ch5_choice_text;
        }
    }

    var _ch5_current_file = file_text_open_write(""ch5_translation_current.txt"");
    file_text_write_string(_ch5_current_file, _ch5_bridge_text);
    file_text_close(_ch5_current_file);

    var _ch5_dialogue_file = file_text_open_write(""ch5_translation_dialogue.txt"");
    file_text_write_string(_ch5_dialogue_file, _ch5_full_text);
    file_text_close(_ch5_dialogue_file);
}";

string readyChoicerCode = @"
function scr_readychoicer(arg0 = """", arg1 = """", arg2 = """", arg3 = """", arg4 = -1, arg5 = -1)
{
    global.msc = -99;
    global.choice = -1;
    global.choicemsg = [arg0, arg1, arg2, arg3];

    var _ch5_choice_text = """";
    for (var _ch5_i = 0; _ch5_i < 4; _ch5_i++)
    {
        var _ch5_choice_line = string(global.choicemsg[_ch5_i]);
        if (_ch5_choice_line != """" && _ch5_choice_line != "" "" && _ch5_choice_line != ""undefined"")
        {
            _ch5_choice_text += string(_ch5_i + 1) + "": "" + _ch5_choice_line + chr(10);
        }
    }
    if (_ch5_choice_text != """")
    {
        var _ch5_base_text = """";
        if (variable_global_exists(""ch5_bridge_dialogue""))
        {
            _ch5_base_text = global.ch5_bridge_dialogue + chr(10);
        }
        var _ch5_dialogue_file = file_text_open_write(""ch5_translation_dialogue.txt"");
        file_text_write_string(_ch5_dialogue_file, _ch5_base_text + ""[CHOICE]"" + chr(10) + _ch5_choice_text);
        file_text_close(_ch5_dialogue_file);
    }

    var count = 2;
    if (arg2 != """")
    {
        count++;
    }
    if (arg3 != """")
    {
        count++;
    }
    var chooseString = ""\\C"" + string(count);
    if (arg4 == -1 && instance_exists(obj_cutscene_master))
    {
        arg4 = true;
    }
    if (arg5)
    {
        if (arg4)
        {
            c_msgset(0, chooseString);
        }
        else
        {
            msgset(0, chooseString);
        }
    }
    else if (arg4)
    {
        c_msgnext(chooseString);
    }
    else
    {
        msgnext(chooseString);
    }
}";

string choicerAdjustCode = @"
function scr_choiceradjust(arg0 = 0, arg1 = 0, arg2 = 0, arg3 = 0, arg4 = 0, arg5 = 0, arg6 = 0, arg7 = 0, arg8 = 0, arg9 = 0)
{
    var _ch5_choice_text = """";
    if (variable_global_exists(""choicemsg"") && is_array(global.choicemsg))
    {
        var _ch5_choice_len = min(4, array_length(global.choicemsg));
        for (var _ch5_i = 0; _ch5_i < _ch5_choice_len; _ch5_i++)
        {
            var _ch5_choice_line = string(global.choicemsg[_ch5_i]);
            if (_ch5_choice_line != """" && _ch5_choice_line != "" "" && _ch5_choice_line != ""undefined"")
            {
                _ch5_choice_text += string(_ch5_i + 1) + "": "" + _ch5_choice_line + chr(10);
            }
        }
    }
    if (_ch5_choice_text != """")
    {
        var _ch5_base_text = """";
        if (variable_global_exists(""ch5_bridge_dialogue""))
        {
            _ch5_base_text = global.ch5_bridge_dialogue + chr(10);
        }
        var _ch5_dialogue_file = file_text_open_write(""ch5_translation_dialogue.txt"");
        file_text_write_string(_ch5_dialogue_file, _ch5_base_text + ""[CHOICE]"" + chr(10) + _ch5_choice_text);
        file_text_close(_ch5_dialogue_file);
    }

    var choiceradjuster = instance_create_depth(0, 0, 0, obj_object);
    with (choiceradjuster)
    {
        __opt0xoff = arg0;
        __opt0yoff = arg1;
        __opt1xoff = arg2;
        __opt1yoff = arg3;
        __opt2xoff = arg4;
        __opt2yoff = arg5;
        __opt3xoff = arg6;
        __opt3yoff = arg7;
        __heartxoff = arg8;
        __heartyoff = arg9;
        scr_debug_print(""CREATED"");
        
        begin_step_func = function()
        {
            var done = false;
            with (obj_choicer_neo)
            {
                opt0xoff = other.__opt0xoff / 2;
                opt0yoff = other.__opt0yoff / 2;
                opt1xoff = other.__opt1xoff / 2;
                opt1yoff = other.__opt1yoff / 2;
                opt2xoff = other.__opt2xoff / 2;
                opt2yoff = other.__opt2yoff / 2;
                opt3xoff = other.__opt3xoff / 2;
                opt3yoff = other.__opt3yoff / 2;
                heartxoff = other.__heartxoff;
                heartyoff = other.__heartyoff;
                done = true;
            }
            if (done)
            {
                scr_debug_print(""donezo"");
                instance_destroy();
            }
        };
    }
    return choiceradjuster;
}";

CodeImportGroup importGroup = new CodeImportGroup(Data)
{
    AutoCreateAssets = false,
    MainThreadAction = MainThreadAction
};

importGroup.QueueReplace("gml_GlobalScript_msgset", msgsetCode);
importGroup.QueueReplace("gml_GlobalScript_scr_readychoicer", readyChoicerCode);
importGroup.QueueReplace("gml_GlobalScript_scr_choiceradjust", choicerAdjustCode);
importGroup.Import();

ScriptMessage("Patched chapter 5 bridge v7: msgset writes choices when a chooser message is shown.");

#!/usr/bin/env python3
"""Hash-specific stock record identity and preview request map; read-only."""
import hashlib
import json
from pathlib import Path
from index_hid_dispatch import SHA
from index_browser_path import pc_literal, immediate
from index_row_request import built_word

ROOT=Path(__file__).resolve().parents[1]


def movl(data, pc):
    op=int.from_bytes(data[pc:pc+2],'little')
    n=(op>>8)&15;m=(op>>4)&15
    if op>>12==5:return {'direction':'load','base':m,'register':n,'displacement':(op&15)*4}
    if op>>12==1:return {'direction':'store','base':n,'register':m,'displacement':(op&15)*4}
    if op&0xf00f==0x6002:return {'direction':'load','base':m,'register':n,'displacement':0}
    if op&0xf00f==0x2002:return {'direction':'store','base':n,'register':m,'displacement':0}
    raise ValueError('Expected MOV.L memory transfer')


def transfer(data, load, store):
    source=movl(data,load);target=movl(data,store)
    if source['direction']!='load' or target['direction']!='store' or source['register']!=target['register']:
        raise ValueError('Unexpected transfer')
    return {'load_file_offset':load,'store_file_offset':store,'source':source,'target':target}


def analyze(data):
    if hashlib.sha256(data).hexdigest()!=SHA:raise ValueError('Unexpected firmware SHA-256')
    return {'image':'main-040000-unpacked.bin','image_sha256':SHA,
            'address_space':'All instruction locations are FILE offsets. Structure displacements are bytes, not RAM addresses.',
            'method':'Static dataflow only; no patch, device call or firmware execution.',
            'record_reader_entry':0x12920e4,
            'record_main_id':transfer(data,0x129216a,0x129216e),
            'record_artwork_id':transfer(data,0x12921aa,0x12921ac),
            'row_table_offset_literal':pc_literal(data,0x12b8aac),
            'record_reader_literal':pc_literal(data,0x12b8ad2),
            'browser_source_context':{
                'list_handler_entry':0x12a4a90,
                'list_connection_context_offset':0x6c68,
                'connection_save':movl(data,0x12a4b52),
                'connection_type_save':transfer(data,0x12a4ba4,0x12a4ba8),
                'connection_type_override':movl(data,0x12a4bbe),
                'connection_type_restore':movl(data,0x12a4bde),
                'row_kind_store_file_offset':0x12b8ba6,
                'row_kind_from_record':movl(data,0x12b92c0),
                'record_kind_from_message':{'load':movl(data,0x1292186),'store':movl(data,0x129218a),
                     'normalization': 'EXTU.B at file 0x1292188'},
                'artwork_flag':immediate(data,0x12b8bd8)['signed_value']<<8,
                'secondary_flag':immediate(data,0x12b93f2)['signed_value']<<8,
                'request_source_slot':movl(data,0x12900be),
                'request_track_type':movl(data,0x12900c2),
                'common_request_word_store':movl(data,0x12900e2),
                'scope':'Static list-mode path. No live pointer reading, writes, or connection sharing authorized by these offsets.'},
            'row_main_id':transfer(data,0x12b8b80,0x12b8b84),
            'row_artwork_id':transfer(data,0x12b8bce,0x12b8bd4),
            'row_stride':immediate(data,0x12b8d8e)['signed_value']*4,
            'blue_preview':{'entry':0x1293d76,'request':built_word(data,0x1293dce,0x1293dd0,0x1293dd6),
                            'response':built_word(data,0x1293e4c,0x1293e54,0x1293e5c)},
            'blue_call_contract':{
                'callee_frame_bytes':48,
                'arg5_selector':movl(data,0x1293dee),
                'arg6_optional_resource':movl(data,0x1293dec),
                'arg7_optional_kind':movl(data,0x1293e08),
                'caller_entry':0x12cb4ba,
                'caller_query_literal':pc_literal(data,0x12cb528),
                'caller_length_output':transfer(data,0x12cb55e,0x12cb560),
                'caller_buffer_output':transfer(data,0x12cb562,0x12cb564),
                'caller_failure_buffer_load':movl(data,0x12cb548),
                'caller_failure_release_literal':pc_literal(data,0x12cb54e),
                'release_wrapper_file_entry':0x1382a9a,
                'release_allocator_literal':pc_literal(data,0x1382ad2),
                'release_pool_literal':pc_literal(data,0x1382ad4),
                'scope':'r4 connection, r5 ID, r6 length output, r7 buffer output; three stack arguments. Selector semantics and task/source binding remain unverified.'},
            'rgb_call_contract':{
                'entry':0x129626c,'callee_frame_bytes':40,
                'arg5_length_output':movl(data,0x12962a6),
                'arg6_buffer_output':movl(data,0x12962aa),
                'arg7_metadata_output':movl(data,0x12962ac),
                'caller_entry':0x12cbf56,
                'caller_query_literal':pc_literal(data,0x12cbf94),
                'caller_atom_literal':pc_literal(data,0x12cbf98),
                'caller_extension_literal':pc_literal(data,0x12cbf96),
                'waiter_literal':pc_literal(data,0x1296382),
                'waiter_length':transfer(data,0x129120c,0x129120e),
                'waiter_buffer':transfer(data,0x1291214,0x1291216),
                'waiter_metadata':transfer(data,0x1291218,0x129121a),
                'waiter_detach':movl(data,0x129121e),
                'caller_cleanup_release_literal':pc_literal(data,0x12cc2de),
                'scope':'Different waiter from Blue; r4 connection, r5 ID, r6/r7 tag and extension. Metadata meaning and live context remain unverified.'},
            'detailed_waveform':{'entry':0x1295914,'request':built_word(data,0x1295956,0x129595a,0x129596a),
                                  'response':built_word(data,0x129598e,0x1295996,0x129599e)},
            'binary_result_transfer':{
                'waiter_entry':0x12905e0,
                'length':transfer(data,0x12906ce,0x12906d0),
                'buffer':transfer(data,0x12906d4,0x12906d6),
                'detach_store_file_offset':0x12906d8,
                'detach_store':movl(data,0x12906d8),
                'zero_register_instruction':immediate(data,0x12906c0),
                'message_release_literal':pc_literal(data,0x12906e4),
                'scope':'Expected response branch transfers the binary pointer and clears it before message disposal. Full task/allocator contract not established.'},
            'not_proven':['Every row kind is a track: directories and other menu kinds must be excluded.',
                          'Selected row generation, task ownership, lifetime and correct source context.',
                          'Selector semantics and optional-resource meaning; register/stack positions are now traced.',
                          'Runtime hook, loader and tested recovery.']}

if __name__=='__main__':
    result=analyze((ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
    out=ROOT/'evidence/row-identity-v144.json';out.write_text(json.dumps(result,indent=2)+'\n');print(out)

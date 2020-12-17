import torch
from QA_config import config


################################################################################
# Output either True or False if cuda is available for deep learning computations.
def has_cuda():
    # is there even cuda available?
    has_cuda = torch.cuda.is_available()
    if has_cuda:
        # we require cuda version >=3.5
        capabilities = torch.cuda.get_device_capability(torch.cuda.current_device())
        major_version = capabilities[0]
        minor_version = capabilities[1]
        if major_version < 3 or (major_version == 3 and minor_version < 5):
            has_cuda = False
    print(f'Has cuda = {has_cuda}')
    return has_cuda


# Output a torch device to use.
def get_torch_device(gpuid = None):
    # Output a torch device with a preferred gpuid (use -2 to force cpu)
    if not gpuid:
        gpuid = config.getint("cuda","gpuid", fallback=0)

    device = torch.device(gpuid if gpuid != -2 and torch.cuda.is_available() else 'cpu')
    return device

################################################################################


################################################################################
# similar to the unix tail command - from https://stackoverflow.com/a/136368
def get_file_tail(file_path, lines=20):
    f = open(file_path, 'rb')
    total_lines_wanted = lines
    BLOCK_SIZE = 1024
    f.seek(0, 2)
    block_end_byte = f.tell()
    lines_to_go = total_lines_wanted
    block_number = -1
    blocks = []
    while lines_to_go > 0 and block_end_byte > 0:
        if (block_end_byte - BLOCK_SIZE > 0):
            f.seek(block_number*BLOCK_SIZE, 2)
            blocks.append(f.read(BLOCK_SIZE))
        else:
            f.seek(0,0)
            blocks.append(f.read(block_end_byte))
        lines_found = blocks[-1].count(b'\n')
        lines_to_go -= lines_found
        block_end_byte -= BLOCK_SIZE
        block_number -= 1
    all_read_text = b''.join(reversed(blocks))
    return b'\n'.join(all_read_text.splitlines()[-total_lines_wanted:])
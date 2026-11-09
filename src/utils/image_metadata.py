"""Read the metadata exposed by Pillow without decoding the image pixels."""
from datetime import datetime
from pathlib import Path
from collections.abc import Mapping
from xml.etree import ElementTree
from PIL import Image, ExifTags, IptcImagePlugin, ImageCms


def metadata_text(value):
    if isinstance(value, bytes):
        try:
            text = value.decode('utf-8').rstrip('\x00')
            if all(c.isprintable() or c in '\n\r\t' for c in text):
                return text
        except UnicodeDecodeError:
            pass
        return f'{len(value)} octets — hexadécimal :\n{value.hex(" ")}'
    return str(value)


def flatten_metadata(values, prefix=''):
    rows = []
    for key, value in values.items():
        name = f'{prefix} / {key}' if prefix else str(key)
        if isinstance(value, Mapping):
            rows.extend(flatten_metadata(value, name))
        else:
            rows.append((name, metadata_text(value)))
    return rows


def tag_label(tag, labels):
    if isinstance(tag, int):
        return f'{labels.get(tag, "Balise inconnue")} (0x{tag:04X})'
    return str(tag)


def read_image_metadata(filename):
    path = Path(filename)
    stat = path.stat()
    sections = [('Fichier', [('Nom', path.name), ('Chemin complet', str(path.absolute())),
        ('Taille (octets)', str(stat.st_size)),
        ('Dernière modification', datetime.fromtimestamp(stat.st_mtime).isoformat(' ', timespec='seconds')),
        ('Création', datetime.fromtimestamp(getattr(stat, 'st_birthtime', stat.st_ctime)).isoformat(' ', timespec='seconds'))])]
    errors = []
    with Image.open(path) as image:
        sections.append(('Image', [('Format', str(image.format)), ('Description du format', str(image.format_description)),
            ('Dimensions du fichier', f'{image.width} × {image.height} px'), ('Mode', image.mode),
            ('Canaux', ', '.join(image.getbands())), ('Nombre de vues / trames', str(getattr(image, 'n_frames', 1)))]))
        sections.append(('Métadonnées du format', flatten_metadata(image.info)))
        segments = getattr(image, 'applist', None)
        if segments:
            sections.append(('Segments JPEG intégrés', [(f'{marker} [{index}]', metadata_text(data))
                for index, (marker, data) in enumerate(segments, 1)]))
        # PNG textual chunks, including chunks not copied into info yet.
        text = getattr(image, 'text', None)
        if text:
            sections.append(('Textes intégrés', flatten_metadata(text)))
        try:
            exif = image.getexif()
            sections.append(('EXIF — IFD0', [(tag_label(tag, ExifTags.TAGS), metadata_text(value))
                                           for tag, value in exif.items()]))
            for tag, title in [(34665, 'EXIF — Prise de vue'), (34853, 'EXIF — GPS'),
                               (40965, 'EXIF — Interopérabilité'), (37500, 'EXIF — Fabricant'), (-1, 'EXIF — Miniature / IFD1')]:
                try:
                    if tag in (40965, 37500) and tag not in exif.get_ifd(34665):
                        continue
                    values = exif.get_ifd(tag)
                    labels = ExifTags.GPSTAGS if tag == 34853 else ExifTags.TAGS
                    if values:
                        sections.append((title, flatten_metadata({tag_label(k, labels): v for k, v in values.items()})))
                except Exception as error:
                    errors.append(f'{title} : {error}')
        except Exception as error:
            errors.append(f'EXIF : {error}')
        tags = getattr(image, 'tag_v2', None)
        if tags:
            sections.append(('TIFF — Toutes les balises', [(f'{ExifTags.TAGS.get(k, k)} ({k})', metadata_text(v))
                                                           for k, v in tags.items()]))
        try:
            iptc = IptcImagePlugin.getiptcinfo(image)
            if iptc:
                sections.append(('IPTC', flatten_metadata(iptc)))
        except Exception as error:
            errors.append(f'IPTC : {error}')
        xmp = image.info.get('xmp') or image.info.get('XML:com.adobe.xmp')
        if xmp:
            try:
                rows = []
                def visit(element, prefix=''):
                    name = f'{prefix}/{element.tag}'
                    for key, value in element.attrib.items():
                        rows.append((f'{name}/@{key}', value))
                    if element.text and element.text.strip():
                        rows.append((name, element.text.strip()))
                    for child in element:
                        visit(child, name)
                visit(ElementTree.fromstring(xmp))
                if rows:
                    sections.append(('XMP', rows))
            except Exception as error:
                errors.append(f'XMP : {error}')
        if image.info.get('icc_profile'):
            try:
                import io
                profile = ImageCms.ImageCmsProfile(io.BytesIO(image.info['icc_profile']))
                sections.append(('Profil ICC', [('Nom', ImageCms.getProfileName(profile)),
                    ('Description', ImageCms.getProfileDescription(profile)), ('Informations', ImageCms.getProfileInfo(profile))]))
            except Exception as error:
                errors.append(f'Profil ICC : {error}')
    if errors:
        sections.append(('Métadonnées non décodées', [('Détail', '\n'.join(errors))]))
    return [(title, rows) for title, rows in sections if rows]

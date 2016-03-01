package eu.nomad_lab.parsers

import eu.{nomad_lab=>lab}
import eu.nomad_lab.DefaultPythonInterpreter
import org.{json4s => jn}
import scala.collection.breakOut

object DlPolyParser extends SimpleExternalParserGenerator(
  name = "DlPolyParser",
  parserInfo = jn.JObject(
    ("name" -> jn.JString("DlPolyParser")) ::
      ("parserId" -> jn.JString("DlPolyParser" + lab.DlPolyVersionInfo.version)) ::
      ("versionInfo" -> jn.JObject(
        ("nomadCoreVersion" -> jn.JString(lab.NomadCoreVersionInfo.version)) ::
          (lab.DlPolyVersionInfo.toMap.map{ case (key, value) =>
            (key -> jn.JString(value.toString))
          }(breakOut): List[(String, jn.JString)])
      )) :: Nil
  ),
  mainFileTypes = Seq("text/.*"),
  mainFileRe = """ DL_POLY """.r,
  cmd = Seq(DefaultPythonInterpreter.python2Exe(), "${envDir}/parsers/dl_poly/parser/parser-dl_poly/SimpleDL_POLYParser.py",
    "--uri", "${mainFileUri}", "${mainFilePath}"),
  resList = Seq(
    "parser-dl_poly/SimpleDL_POLYParser.py",
    "parser-dl_poly/setup_paths.py",
    "nomad_meta_info/common.nomadmetainfo.json",
    "nomad_meta_info/meta_types.nomadmetainfo.json",
    "nomad_meta_info/dl_poly.nomadmetainfo.json"
  ) ++ DefaultPythonInterpreter.commonFiles(),
  dirMap = Map(
    "parser-dl_poly" -> "parsers/dl_poly/parser/parser-dl_poly",
    "nomad_meta_info" -> "nomad-meta-info/meta_info/nomad_meta_info"
  ) ++ DefaultPythonInterpreter.commonDirMapping()
)

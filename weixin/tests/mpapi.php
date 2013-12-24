<?php
ini_set('display_errors', 'On');
error_reporting(E_ALL);
define("TOKEN","bWFnaWNfbXA");

function checkSignature()
{
    $signature = $_GET["signature"];
    $timestamp = $_GET["timestamp"];
    $nonce = $_GET["nonce"];

    $token = TOKEN;
    $tmpArr = array($token, $timestamp, $nonce);
    sort($tmpArr);
    $tmpStr = implode( $tmpArr );
    $tmpStr = sha1( $tmpStr );

    if( $tmpStr == $signature ){
        return true;
    }else{
        return false;
    }
}

if (checkSignature()) {
    echo $_GET['echostr'];
} else {
    echo "Checking error";
}
?>

